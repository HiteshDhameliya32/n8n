# Fixes Applied

## Issue Fixed: Internal Server Error (500) on Job Description Upload

### Problem
- Files were being read from memory after saving to database, causing errors
- Pinecone deletion was not implemented

### Solution

#### 1. File Upload Flow Fixed
**Changed approach:**
- **Before**: Tried to read file from memory after saving (file object can only be read once)
- **After**: 
  1. Save file to database first (Django saves it to disk)
  2. Read file from disk as binary
  3. Send binary file to webhook

**Files modified:**
- `manager/views.py` - `upload_resume_file()` function
- `manager/views.py` - `upload_job_description()` function

**Key changes:**
```python
# Step 1: Save to database (saves file to disk)
resume = Resume.objects.create(file=resume_file, ...)

# Step 2: Read from disk as binary
with open(resume.file.path, 'rb') as file_on_disk:
    file_content = file_on_disk.read()

# Step 3: Send binary to webhook
files = {'file': (resume.file_name, file_content, 'application/pdf')}
```

#### 2. Pinecone Deletion Implemented
**Based on provided sample code:**
- Uses `file-name` (with hyphen) as metadata filter key
- Queries Pinecone index to find all vectors for the file
- Deletes all matching vectors by ID

**Implementation:**
- `manager/views.py` - `delete_from_pinecone()` function
- Uses Pinecone client to query and delete vectors
- Handles errors gracefully (doesn't block deletion if Pinecone fails)

**Key features:**
- Searches for vectors with `metadata.file-name == file_name`
- Uses dummy zero vector for query (as per sample code)
- Deletes all found vector IDs
- Includes proper error handling

#### 3. Dependencies Added
**Updated `requirements.txt`:**
- `pinecone-client>=3.0.0` - For Pinecone operations
- `numpy>=1.24.0` - For vector operations

## Configuration Required

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Pinecone Settings
In `resumeManager/settings.py` or environment variables:
```python
PINECONE_API_KEY = 'pcsk_61YV5B_FbKgzNgPpHSHQWaLhTBAkMzk2coPCs3LLEu3yeHqBFpqNytrt3JwNWFp9pqHYU7'
PINECONE_INDEX_NAME = 'n8n-rag-chat-bot'  # Or your index name
```

### 3. Adjust Vector Dimension (if needed)
In `manager/views.py`, line 307:
```python
query_vector = np.zeros(768).tolist()  # Adjust if your vectors are different dimension
```
Common dimensions:
- 384 (sentence-transformers)
- 768 (BERT) - default
- 1536 (OpenAI ada-002)

### 4. Configure Webhook URLs
```python
JOB_DESCRIPTION_WEBHOOK_URL = 'https://your-webhook-url.com/job-description'
RESUME_WEBHOOK_URL = 'https://your-webhook-url.com/resume'
```

## Testing

1. **Test Resume Upload:**
   - Upload a PDF resume
   - Check that file is saved to database
   - Verify webhook receives binary file
   - Check analysis data is stored

2. **Test Job Description Upload:**
   - Upload a job description file
   - Check that file is saved to database
   - Verify webhook receives binary file


---

# Latest Fixes Applied (November 14, 2025)

## Task 1: Fixed X-Frame-Options 'deny' Error ✅

### Problem
The error "Refused to display 'http://127.0.0.1:8000/' in a frame because it set 'X-Frame-Options' to 'deny'" was appearing in the browser console, preventing iframes from loading properly.

### Solution
1. Created custom middleware (`manager/middleware.py`) - `ConditionalXFrameOptionsMiddleware`
   - Respects the `X_FRAME_OPTIONS` setting from Django settings
   - Allows views to override the header if needed
   
2. Updated `resumeManager/settings.py`
   - Changed middleware from Django's default to custom: `'manager.middleware.ConditionalXFrameOptionsMiddleware'`
   - Set `X_FRAME_OPTIONS = 'SAMEORIGIN'` to allow same-origin iframes
   
3. Added Favicon
   - Created `manager/static/favicon.ico`
   - Added favicon link to `manager/templates/base.html` to eliminate 404 errors

**Files Modified:**
- `manager/middleware.py` (new)
- `resumeManager/settings.py`
- `manager/templates/base.html`
- `manager/static/favicon.ico` (new)

---

## Task 2: Fixed PDF Preview Issue ✅

### Problem
Resume PDF was not previewing in the analysis page despite the file being available.

### Solution
1. Changed from `<iframe>` to `<embed>` tag (`manager/templates/analysis.html`)
   - More compatible with PDF viewing
   - Set proper MIME type: `type="application/pdf"`
   
2. Improved PDF loading logic (`manager/static/js/analysis.js`)
   - Added URL absolutization: converts relative URLs to absolute URLs
   - Fixed error handling for embed tags
   - Better fallback messaging

3. Enhanced download response (`manager/views.py`)
   - Improved error handling in `download_resume()`
   - Added file existence validation before serving
   - Proper headers for PDF serving

**Files Modified:**
- `manager/templates/analysis.html`
- `manager/static/js/analysis.js`
- `manager/views.py`

---

## Task 3: Added Calendar View to Interview Scheduling ✅

### Problem
Users had no visibility into their existing calendar events when scheduling interviews, risking conflicts.

### Solution
1. Redesigned interview scheduling modal with 2-column layout
   - **Left**: Email composition form
   - **Right**: Calendar events viewer
   
2. Implemented calendar event fetching
   - `loadCalendarEvents()` - Fetches upcoming events from Google Calendar
   - `selectEventTime()` - Allows users to click events to auto-fill interview time
   
3. Calendar features
   - Shows upcoming events from Google Calendar (next 30 days)
   - Displays event title and date/time
   - Clickable events pre-fill interview date/time
   - Visual feedback when event is selected
   - Graceful fallback when calendar not connected

**Files Modified:**
- `manager/static/js/analysis.js` (enhanced modal and added helper functions)

---

## Task 4: Added Settings Page for Google Calendar & Gmail Credentials ✅

### New Model
**GoogleCalendarSettings** (`manager/models.py`)
- Stores Google Calendar and Gmail API credentials
- Fields: `google_client_id`, `google_client_secret`, `google_refresh_token`, `gmail_address`, `calendar_id`, `is_connected`, `last_synced`

### New Views
- `settings_page()` - Settings page display
- `google_calendar_auth()` - Initiates Google OAuth flow
- `google_calendar_callback()` - Handles OAuth callback
- `google_calendar_disconnect()` - Disconnects Google account
- `get_google_calendar_events()` - Fetches upcoming calendar events

### New Routes
- `GET /settings/` - Settings page
- `POST /api/google-calendar/auth/` - Start OAuth flow
- `GET /api/google-calendar/callback/` - OAuth callback
- `POST /api/google-calendar/disconnect/` - Disconnect account
- `GET /api/google-calendar/events/` - Get calendar events

### New Templates
1. **settings.html** - Settings page with Google Calendar integration
   - Status display (connected/disconnected)
   - Connect/Disconnect/Reconnect buttons
   - Setup instructions
   - Responsive design

2. **google_callback.html** - OAuth callback page
   - Success/error messaging
   - Auto-close window after authentication
   - Parent window reload notification

### Configuration Required
Add to `.env` file:
```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

### Setup Instructions
1. Navigate to Settings page (new link in navigation)
2. Click "Connect Google Account"
3. Sign in with Google
4. Grant permissions for Calendar and Gmail
5. You'll be redirected and connection status updates

**Files Modified/Created:**
- `manager/models.py` (added `GoogleCalendarSettings`)
- `manager/views.py` (added 5 new functions)
- `manager/urls.py` (added 5 new routes + settings)
- `manager/templates/base.html` (added Settings nav link)
- `manager/templates/settings.html` (new)
- `manager/templates/google_callback.html` (updated)
- `manager/migrations/0005_googlecalendarsettings.py` (auto-created)

---

## Database Changes
```bash
python manage.py makemigrations  # Creates migration for GoogleCalendarSettings
python manage.py migrate          # Applies migration
```

---

## Summary of All Changes
| Task | Status | Files Modified | Impact |
|------|--------|-----------------|--------|
| X-Frame-Options fix | ✅ | 4 files | Fixed iframe security headers |
| PDF preview | ✅ | 3 files | PDFs now display in analysis page |
| Calendar integration | ✅ | 1 file | Users see their calendar when scheduling |
| Settings page | ✅ | 7 files + migration | Users can connect Google accounts |

---

## Testing Checklist
- [ ] PDF preview works in analysis page
- [ ] Download PDF button works
- [ ] No X-Frame-Options errors
- [ ] Settings page accessible from navigation
- [ ] Google OAuth flow works
- [ ] Calendar events display in scheduling modal
- [ ] Clicking events pre-fills date/time
- [ ] Disconnect/Reconnect works
- [ ] Proper error messages display

---

## Security Notes
1. OAuth tokens stored securely in database
2. Google credentials in `.env` file (never committed)
3. CSRF protection on all API endpoints
4. X-Frame-Options set to SAMEORIGIN for security

---

## Future Enhancements
- Email scheduling and automation
- Calendar auto-sync for scheduled interviews
- Timezone support
- Multiple calendar selection
- Calendar invites to candidates
3. **Test Pinecone Deletion:**
   - Upload a job description
   - Delete the job description
   - Check console/logs for Pinecone deletion messages
   - Verify vectors are deleted from Pinecone

## Error Handling

- File existence check before reading
- Graceful handling of Pinecone errors (doesn't block deletion)
- Proper error messages returned to frontend
- Database cleanup on webhook failures

## Notes

- Files are now stored first, then sent to webhook as binary
- Pinecone deletion uses `file-name` metadata key (with hyphen)
- Vector dimension is set to 768 (adjust if needed)
- All file operations use binary mode for proper handling

