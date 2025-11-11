from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional
import boto3
from botocore.client import Config
import json
import os
from datetime import datetime
import uuid

app = FastAPI(title="Recommendations Wall API")

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


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the front-end HTML page"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recommendations Wall - Cloud Storage Demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        .stars {
            display: flex;
            gap: 5px;
        }
        .star {
            font-size: 30px;
            cursor: pointer;
            color: #ddd;
            transition: color 0.2s;
        }
        .star.active { color: #ffc107; }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: #5568d3; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card h3 { font-size: 1.2em; margin-bottom: 5px; }
        .stat-card .number { font-size: 2em; font-weight: bold; }
        .reviews-list {
            display: grid;
            gap: 15px;
        }
        .review-item {
            border-left: 4px solid #667eea;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .review-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .review-title { font-weight: 600; font-size: 1.1em; }
        .review-tag {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
        }
        .example-json {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            margin-top: 10px;
        }
        .json-key { color: #9cdcfe; }
        .json-string { color: #ce9178; }
        .json-number { color: #b5cea8; }
        .success { color: #28a745; font-weight: 600; margin-top: 10px; }
        .error { color: #dc3545; font-weight: 600; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Recommendations Wall</h1>
            <p>Cloud Storage Demo: Each review = 1 JSON file in object storage!</p>
        </div>

        <div class="card">
            <h2>🎯 Top Tags Right Now</h2>
            <div class="stats" id="stats"></div>
        </div>

        <div class="card">
            <h2>✍️ Add Your Recommendation</h2>
            <form id="reviewForm">
                <div class="form-group">
                    <label>What are you recommending? *</label>
                    <input type="text" id="title" placeholder="e.g., The Matrix, Chocolate Cake, Python" required>
                </div>
                <div class="form-group">
                    <label>Tag/Genre *</label>
                    <input type="text" id="tag" placeholder="e.g., Movie, Recipe, Language" required>
                </div>
                <div class="form-group">
                    <label>Rating *</label>
                    <div class="stars" id="stars">
                        <span class="star" data-value="1">★</span>
                        <span class="star" data-value="2">★</span>
                        <span class="star" data-value="3">★</span>
                        <span class="star" data-value="4">★</span>
                        <span class="star" data-value="5">★</span>
                    </div>
                    <input type="hidden" id="rating" required>
                </div>
                <div class="form-group">
                    <label>Comment (optional)</label>
                    <textarea id="comment" placeholder="What did you like about it?"></textarea>
                </div>
                <button type="submit">Submit to Cloud ☁️</button>
                <div id="message"></div>
            </form>
        </div>

        <div class="card">
            <h2>💾 Example: How Your Review is Stored</h2>
            <p>When you submit, the API creates a JSON file like this in Cloudflare R2:</p>
            <div class="example-json">
<span class="json-key">{
  "id"</span>: <span class="json-string">"a1b2c3d4-1234-5678-9abc-def012345678"</span>,
  <span class="json-key">"title"</span>: <span class="json-string">"The Matrix"</span>,
  <span class="json-key">"tag"</span>: <span class="json-string">"Movie"</span>,
  <span class="json-key">"stars"</span>: <span class="json-number">5</span>,
  <span class="json-key">"comment"</span>: <span class="json-string">"Mind-bending action!"</span>,
  <span class="json-key">"timestamp"</span>: <span class="json-string">"2025-11-11T14:30:00Z"</span>
}</div>
            <p style="margin-top: 10px; color: #666;">
                📁 Saved as: <code>reviews/a1b2c3d4-1234-5678-9abc-def012345678.json</code>
            </p>
        </div>

        <div class="card">
            <h2>📖 Recent Reviews</h2>
            <div class="reviews-list" id="reviews"></div>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin;
        let selectedRating = 0;

        // Star rating interaction
        document.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', function() {
                selectedRating = parseInt(this.dataset.value);
                document.getElementById('rating').value = selectedRating;
                document.querySelectorAll('.star').forEach((s, i) => {
                    s.classList.toggle('active', i < selectedRating);
                });
            });
        });

        // Load stats and reviews
        async function loadData() {
            try {
                const response = await fetch(`${API_URL}/top`);
                const data = await response.json();
                
                // Display stats
                const statsHtml = data.top_tags.slice(0, 4).map(item => `
                    <div class="stat-card">
                        <h3>${item.tag}</h3>
                        <div class="number">${item.count}</div>
                        <div>${'⭐'.repeat(Math.round(item.avg_stars))}</div>
                    </div>
                `).join('');
                document.getElementById('stats').innerHTML = statsHtml || '<p>No recommendations yet!</p>';

                // Display recent reviews
                const reviewsHtml = data.recent_reviews.map(review => `
                    <div class="review-item">
                        <div class="review-header">
                            <span class="review-title">${review.title}</span>
                            <span class="review-tag">${review.tag}</span>
                        </div>
                        <div>${'⭐'.repeat(review.stars)}</div>
                        ${review.comment ? `<p style="margin-top: 8px; color: #666;">${review.comment}</p>` : ''}
                    </div>
                `).join('');
                document.getElementById('reviews').innerHTML = reviewsHtml || '<p>Be the first to recommend something!</p>';
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        // Submit form
        document.getElementById('reviewForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const messageEl = document.getElementById('message');
            
            if (!selectedRating) {
                messageEl.innerHTML = '<div class="error">Please select a rating!</div>';
                return;
            }

            const review = {
                title: document.getElementById('title').value,
                tag: document.getElementById('tag').value,
                stars: selectedRating,
                comment: document.getElementById('comment').value || null
            };

            try {
                const response = await fetch(`${API_URL}/reviews`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(review)
                });

                if (response.ok) {
                    messageEl.innerHTML = '<div class="success">✅ Saved to cloud storage!</div>';
                    e.target.reset();
                    selectedRating = 0;
                    document.querySelectorAll('.star').forEach(s => s.classList.remove('active'));
                    setTimeout(() => loadData(), 500);
                } else {
                    const error = await response.json();
                    messageEl.innerHTML = `<div class="error">❌ ${error.detail}</div>`;
                }
            } catch (error) {
                messageEl.innerHTML = '<div class="error">❌ Connection error</div>';
            }
        });

        // Load data on page load
        loadData();
        setInterval(loadData, 30000); // Refresh every 30 seconds
    </script>
</body>
</html>
    """


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
