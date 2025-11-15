# AI Resume Checker - Frontend Application

A RAG-based AI Resume Checker web application with 4 main pages: Dashboard, Resume Upload, Resume Analysis, and Job Description Management.

## Project Structure

```
resumeManager/
├── manager/
│   ├── templates/
│   │   ├── base.html              # Base template with navigation
│   │   ├── home.html              # Dashboard page
│   │   ├── upload_resume.html     # Resume upload page
│   │   ├── analysis.html          # Resume analysis page
│   │   └── job_descriptions.html  # Job description management page
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css           # Main stylesheet with responsive design
│   │   └── js/
│   │       ├── main.js            # Common utilities and modal functionality
│   │       ├── dashboard.js       # Dashboard functionality
│   │       ├── upload.js          # Upload page functionality
│   │       ├── analysis.js        # Analysis page functionality
│   │       └── job_descriptions.js # Job descriptions page functionality
│   └── views.py                   # Django views (frontend only)
├── resumeManager/
│   ├── settings.py                # Django settings
│   └── urls.py                    # URL configuration
└── README.md                      # This file
```

## Features

### 1. Home Page (Dashboard)
- ✅ Display all uploaded resumes in a table
- ✅ Columns: Candidate Name, Email, Job Description, Upload Date, Overall Score
- ✅ Action buttons: View Analysis, Re-analyze, Delete Resume
- ✅ Search functionality by candidate name, email, or job description
- ✅ Filter by score range and job description
- ✅ Summary widgets: Total resumes, average score, top matched skills
- ✅ Shortcut button to navigate to Resume Upload Page
- ✅ Pagination support

### 2. Resume Upload Page
- ✅ Form to upload resume (PDF only)
- ✅ Text area to paste job description or select from saved job descriptions
- ✅ Candidate info fields: Name, Email
- ✅ File drag-and-drop support
- ✅ Progress indicator showing processing progress
- ✅ Form validation
- ✅ Success/error messages

### 3. Resume Analysis Page
- ✅ Candidate summary card with Name, Email, Overall Score
- ✅ Skill match visualization with progress bars
- ✅ Experience & Education highlights
- ✅ RAG AI chat interface for HR questions
- ✅ Suggested questions for quick queries
- ✅ Export buttons for PDF/CSV reports
- ✅ Re-analyze functionality

### 4. Job Description Management Page
- ✅ Table of stored job descriptions with metadata
- ✅ Add/Edit/Delete job description functionality
- ✅ Modal forms for add/edit operations
- ✅ Assign job descriptions to resumes
- ✅ Form validation

## Design Features

- ✅ Modern, responsive UI design
- ✅ Consistent styling across all pages
- ✅ Reusable components (cards, tables, progress bars, buttons, forms)
- ✅ Navigation bar across all pages
- ✅ Mobile-friendly responsive design
- ✅ Clean and professional HR tool aesthetic
- ✅ Smooth animations and transitions
- ✅ Accessible color scheme and contrast

## Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS)
- **Framework**: Django (for templating and routing)
- **Styling**: Custom CSS with CSS Variables
- **JavaScript**: ES6+ with modular structure

## Getting Started

### Prerequisites
- Python 3.8+
- Django 5.0.7+

### Installation

1. Install Django (if not already installed):
```bash
pip install django
```

2. Run migrations (if needed):
```bash
python manage.py migrate
```

3. Run the development server:
```bash
python manage.py runserver
```

4. Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

## Pages Overview

### Dashboard (`/`)
- View all uploaded resumes
- Search and filter resumes
- View summary statistics
- Quick actions on resumes

### Upload Resume (`/upload/`)
- Upload PDF resumes
- Enter candidate information
- Select or paste job description
- Monitor upload and analysis progress

### Resume Analysis (`/analysis/<resume_id>/`)
- View detailed candidate analysis
- See skill matches and scores
- Chat with AI assistant about candidate
- Export analysis reports

### Job Description Management (`/job-descriptions/`)
- Manage saved job descriptions
- Add, edit, delete job descriptions
- Assign job descriptions to resumes

## API Integration Notes

The frontend is ready for backend integration. All JavaScript files include commented sections showing where API calls should be made. Currently, the application uses sample data for demonstration purposes.

### API Endpoints to Implement:

1. **Dashboard**
   - `GET /api/resumes/` - Get all resumes
   - `POST /api/resumes/<id>/reanalyze/` - Re-analyze resume
   - `DELETE /api/resumes/<id>/` - Delete resume
   - `GET /api/job-descriptions/` - Get job descriptions

2. **Upload**
   - `POST /api/upload-resume/` - Upload and analyze resume
   - `GET /api/job-descriptions/` - Get job descriptions

3. **Analysis**
   - `GET /api/analysis/<resume_id>/` - Get analysis data
   - `POST /api/analysis/<resume_id>/chat/` - Send chat message
   - `POST /api/analysis/<resume_id>/reanalyze/` - Re-analyze
   - `GET /api/analysis/<resume_id>/export/pdf/` - Export PDF
   - `GET /api/analysis/<resume_id>/export/csv/` - Export CSV

4. **Job Descriptions**
   - `GET /api/job-descriptions/` - Get all job descriptions
   - `POST /api/job-descriptions/` - Create job description
   - `PUT /api/job-descriptions/<id>/` - Update job description
   - `DELETE /api/job-descriptions/<id>/` - Delete job description
   - `GET /api/resumes/` - Get resumes for assignment

## Customization

### Colors and Theme
Edit CSS variables in `manager/static/css/main.css`:
```css
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    /* ... more variables ... */
}
```

### Components
All reusable components are defined in `main.css`:
- Buttons (`.btn`, `.btn-primary`, `.btn-secondary`, etc.)
- Cards (`.card`)
- Forms (`.form-input`, `.form-select`, `.form-textarea`)
- Tables (`.data-table`)
- Modals (`.modal`)
- Progress bars (`.progress-bar`)

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Future Enhancements

- [ ] Backend API integration
- [ ] RAG AI implementation
- [ ] Resume parsing and extraction
- [ ] Advanced filtering and sorting
- [ ] Bulk operations
- [ ] User authentication
- [ ] Export functionality
- [ ] Real-time updates
- [ ] Advanced analytics

## Notes

- All forms include CSRF token support for Django
- JavaScript uses modern ES6+ syntax
- CSS uses CSS Variables for easy theming
- All pages are responsive and mobile-friendly
- Sample data is used for demonstration (replace with API calls)

## License

This project is part of a Django application for AI Resume Checking.

---

**Note**: This is a frontend-focused implementation. Backend API endpoints need to be implemented to connect with the RAG AI system and database.

