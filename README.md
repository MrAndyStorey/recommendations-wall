# Recommendations Wall

This is a simple web application that uses a FastAPI server running on a web application server, leveraging **object storage** concepts for Year 12 students. 

Each review is stored as a JSON file in cloud object storage.  The files are all stored in a single **bucket** called *recommendations-wall*, which keeps the data organised.

**Object storage** offers *scalability* as it can store millions of files, it is cost-efficient as you only pay for what you use (this is running on their free tier), and it is reliable as the data is replicated across numerous data centres.

## What Students Learn
* *Cloud Storage:* Each review is a single JSON file stored as an object in the cloud.
* *RESTful APIs:* We use different methods to create (**POST**) or retrieve data (**GET**).
* *Data at rest:* Using Cloudflare's R2 object storage
* *Data in transit:* Using **HTTPS** to **encrypt** the data in transit to/from the server
* *Data Validation:* Input sanitisation and structure
* *Environment Variables:* Keeping credentials secure


## Each JSON File Contains
```
json{
  "id": "unique-uuid",
  "title": "The Matrix",
  "tag": "Movie",
  "stars": 5,
  "comment": "Mind-bending action!",
  "timestamp": "2025-11-11T14:30:00Z"
}
```

## API Endpoints
`GET /` - Front-end interface

`POST /reviews` - Submit a review

`GET /top` - View statistics

`GET /health` - Health check
