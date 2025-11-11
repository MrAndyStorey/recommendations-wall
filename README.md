# recommendations-wall

This is a simple web application that uses a web application server running FastAPI that uses cloud object storage concepts for Year 12 students. 

Each review is stored as a JSON file in object storage (Cloudflare R2).

## What Students Learn
* Cloud Storage: Each review is a single JSON file stored as an object in the cloud.
* RESTful APIs: We use different methods to create (POST) or retrieve data (GET).
* Data at rest: Using Cloudflare's R2 object storage
* Data in transit: Using HTTPS to encrypt the data to/from the server
* Data Validation: Input sanitisation and structure
* Environment Variables: Keeping credentials secure


## Each JSON File Contains
json{
  "id": "unique-uuid",
  "title": "The Matrix",
  "tag": "Movie",
  "stars": 5,
  "comment": "Mind-bending action!",
  "timestamp": "2025-11-11T14:30:00Z"
}

