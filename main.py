from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from typing import Optional
import boto3
from botocore.client import Config
import json
import os
from datetime import datetime
import uuid

app = FastAPI(title="Recommendations Wall API")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS for front-end access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# R2/S3-compatible client setup (Cloudflare R2)
# Students: these credentials come from environment variables for security
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

BUCKET_NAME = os.getenv('R2_BUCKET_NAME', 'recommendations-wall')

# Data model - what students can submit
class Review(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    tag: str = Field(..., min_length=1, max_length=30)
    stars: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=300)
    
    @validator('title', 'tag', 'comment')
    def no_email_or_phone(cls, v):
        """Basic PII protection - no emails or phone patterns"""
        if v and ('@' in v or any(char.isdigit() for char in v.replace(' ', '')[:15])):
            if '@' in v or v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')[:10].isdigit():
                raise ValueError('Please do not include personal information')
        return v


@app.get("/")
async def home(request: Request):
    """Serve the front-end HTML page using Jinja2 template"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/reviews")
async def create_review(review: Review):
    """
    Save a review as a JSON file in object storage.
    Students: This shows how APIs store data in the cloud!
    """
    try:
        # Generate unique ID and timestamp
        review_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Build the complete review object
        review_data = {
            "id": review_id,
            "title": review.title,
            "tag": review.tag,
            "stars": review.stars,
            "comment": review.comment,
            "timestamp": timestamp
        }
        
        # Save as JSON file in object storage
        key = f"reviews/{review_id}.json"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(review_data),
            ContentType='application/json'
        )
        
        return {
            "success": True,
            "id": review_id,
            "message": "Review saved to cloud storage!",
            "storage_path": key
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")


@app.get("/top")
async def get_top_tags():
    """
    Read JSON files from storage and compute statistics.
    Students: This demonstrates reading from object storage via HTTPS!
    """
    try:
        # List all review files
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix='reviews/'
        )
        
        if 'Contents' not in response:
            return {"top_tags": [], "recent_reviews": []}
        
        reviews = []
        
        # Fetch each JSON file (limit to most recent 50 for demo)
        for obj in sorted(response['Contents'], 
                         key=lambda x: x['LastModified'], 
                         reverse=True)[:50]:
            try:
                file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                review_data = json.loads(file_obj['Body'].read())
                reviews.append(review_data)
            except Exception as e:
                print(f"Error reading {obj['Key']}: {e}")
                continue
        
        # Calculate stats by tag
        tag_stats = {}
        for review in reviews:
            tag = review['tag']
            if tag not in tag_stats:
                tag_stats[tag] = {'count': 0, 'total_stars': 0}
            tag_stats[tag]['count'] += 1
            tag_stats[tag]['total_stars'] += review['stars']
        
        # Format top tags
        top_tags = [
            {
                "tag": tag,
                "count": stats['count'],
                "avg_stars": round(stats['total_stars'] / stats['count'], 1)
            }
            for tag, stats in sorted(
                tag_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
        ]
        
        return {
            "top_tags": top_tags,
            "recent_reviews": reviews[:10],
            "total_reviews": len(reviews)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading storage: {str(e)}")


@app.get("/health")
async def health_check():
    """Simple health check for Render"""
    return {"status": "healthy", "storage": "connected"}
  
