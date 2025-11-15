# Setup Guide for AI Resume Checker

## Prerequisites

- Python 3.8+
- Django 5.0.7+
- pip

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create a superuser (optional, for admin access):
```bash
python manage.py createsuperuser
```

## Configuration

### Environment Variables

Create a `.env` file or set the following environment variables:

```bash
# Webhook URLs - TODO: Configure these with your actual webhook URLs
JOB_DESCRIPTION_WEBHOOK_URL=https://your-webhook-url.com/job-description
RESUME_WEBHOOK_URL=https://your-webhook-url.com/resume

# Pinecone Configuration - TODO: Configure these with your Pinecone credentials
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=your-index-name
```

### Settings Configuration

Alternatively, you can configure these in `resumeManager/settings.py`:

```python
JOB_DESCRIPTION_WEBHOOK_URL = 'https://your-webhook-url.com/job-description'
RESUME_WEBHOOK_URL = 'https://your-webhook-url.com/resume'
PINECONE_API_KEY = 'your-pinecone-api-key'
PINECONE_INDEX_NAME = 'your-index-name'
```

## Running the Application

1. Start the development server:
```bash
python manage.py runserver
```

2. Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

## Features

### Resume Upload
- Upload PDF resumes
- Files are sent to webhook for processing
- Analysis results are stored in database

### Job Description Management
- Upload job description files (PDF, TXT, DOC, DOCX)
- Files are sent to webhook for processing
- Delete job descriptions (triggers Pinecone deletion)

### Dashboard
- View all uploaded resumes
- Search and filter resumes
- View summary statistics

## TODO: Human Intervention Required

### 1. Webhook Configuration
- Configure `JOB_DESCRIPTION_WEBHOOK_URL` in settings or environment variables
- Configure `RESUME_WEBHOOK_URL` in settings or environment variables
- Ensure webhooks are set up to receive files and process them

### 2. Pinecone Integration
- Configure Pinecone API credentials
- Implement `delete_from_pinecone()` function in `manager/views.py`
- The function should delete vectors using file_name as identifier

### 3. Webhook Response Format
- Ensure webhook returns analysis data in the expected format:
  - For resumes: `{ "overall_score": 85, "skills": [...], "experience": [...], "education": [...] }`
  - For job descriptions: Webhook should process and store vectors in Pinecone

### 4. File Storage
- Ensure `media/` directory exists and is writable
- Configure file storage settings for production

### 5. Security
- Change `SECRET_KEY` in production
- Set `DEBUG = False` in production
- Configure `ALLOWED_HOSTS` for production
- Set up proper authentication if needed

## API Endpoints

### Resume Endpoints
- `POST /api/upload-resume/` - Upload a resume file
- `GET /api/resumes/` - Get all resumes
- `DELETE /api/resumes/<id>/delete/` - Delete a resume

### Job Description Endpoints
- `POST /api/upload-job-description/` - Upload a job description file
- `GET /api/job-descriptions/` - Get all job descriptions
- `DELETE /api/job-descriptions/<id>/delete/` - Delete a job description

## Database Models

### Resume
- `file` - Resume file
- `file_name` - Original file name
- `upload_date` - Upload timestamp
- `analysis_data` - JSON field for analysis results
- `overall_score` - Overall match score
- `status` - Processing status (pending, processing, completed, failed)

### JobDescription
- `title` - Job title
- `file` - Job description file
- `file_name` - Original file name (used for Pinecone deletion)
- `upload_date` - Upload timestamp

## Notes

- All file uploads are limited to 10MB
- Resume files must be PDF format
- Job description files can be PDF, TXT, DOC, or DOCX
- Webhook timeouts are set to 5 minutes (300 seconds)
- Pinecone deletion uses file_name as the identifier


