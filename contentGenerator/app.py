from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
WEBHOOK_URL = 'http://localhost:5678/webhook-test/387b3de0-7931-478b-b7d0-9d12c013afc6'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Get data from session if available
    response_data = session.pop('response_data', None)
    submitted_text = session.pop('submitted_text', None)
    submitted_filename = session.pop('submitted_filename', None)
    success = session.pop('success', False)
    error = session.pop('error', None)
    
    return render_template('index.html', 
                         response_data=response_data,
                         submitted_text=submitted_text,
                         submitted_filename=submitted_filename,
                         success=success,
                         error=error)

@app.route('/submit', methods=['POST'])
def submit_form():
    try:
        # Check if file is present
        if 'file' not in request.files:
            flash('No file selected')
            return render_template('index.html', error='No file selected')
        
        file = request.files['file']
        text = request.form.get('text', '').strip()
        
        # Validate inputs
        if file.filename == '':
            flash('No file selected')
            return render_template('index.html', error='No file selected')
        
        if not text:
            flash('Text field is required')
            return render_template('index.html', error='Text field is required')
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Only images are allowed.')
            return render_template('index.html', error='Invalid file type. Only images are allowed.')
        
        # Get filename without saving
        filename = secure_filename(file.filename)
        
        # Prepare data for webhook
        webhook_data = {
            'text': text,
            'filename': filename
        }
        
        # Send file and data to webhook as multipart/form-data
        # Determine content type based on file extension
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(file_extension, 'image/jpeg')
        
        try:
            # Reset file pointer to beginning and send file directly
            file.seek(0)
            files = {'file': (filename, file, content_type)}
            
            response = requests.post(
                WEBHOOK_URL,
                data=webhook_data,
                files=files,
                timeout=45
            )
            
            # Prepare response data
            try:
                # Try to parse JSON response and extract fields
                import json
                json_data = response.json()
                
                # Extract individual fields if response is a list with one item
                if isinstance(json_data, list) and len(json_data) > 0:
                    product_data = json_data[0]
                    
                    # Handle bullet_points as array
                    bullet_points_data = product_data.get('bullet_points', []) or product_data.get('bulletPoints', []) or product_data.get('bullet points', [])
                    
                    if isinstance(bullet_points_data, list) and bullet_points_data:
                        bullet_points_text = '\n'.join(bullet_points_data)
                    else:
                        bullet_points_text = str(bullet_points_data) if bullet_points_data else ''
                    # Capture html field if present so the template can render it as-is
                    parsed_data = {
                        'title': product_data.get('title', ''),
                        'description': product_data.get('description', ''),
                        'tags': product_data.get('tags', ''),
                        'bullet_points': bullet_points_text,
                        'html': product_data.get('html', '') if isinstance(product_data.get('html', ''), str) else '',
                        'raw_json': json.dumps(json_data, indent=2, ensure_ascii=False)
                    }
                else:
                    # If not expected format, show raw JSON
                    parsed_data = {
                        'title': '',
                        'description': '',
                        'tags': '',
                        'bullet_points': '',
                        'html': '',
                        'raw_json': json.dumps(json_data, indent=2, ensure_ascii=False)
                    }
            except:
                # If not JSON, use raw text
                # If the webhook returned pure HTML/text, detect HTML and pass it through
                raw_text = response.text or ''
                html_field = ''
                # Basic detection for HTML content
                if isinstance(raw_text, str) and ('<' in raw_text and '>' in raw_text):
                    html_field = raw_text

                parsed_data = {
                    'title': '',
                    'description': '',
                    'tags': '',
                    'bullet_points': '',
                    'html': html_field,
                    'raw_json': raw_text
                }
            
            response_data = {
                'status_code': response.status_code,
                'parsed_data': parsed_data,
                'headers': dict(response.headers),
                'success': response.status_code == 200
            }
            
            
            # Store response data in session and redirect to prevent resubmission on reload
            session['response_data'] = response_data
            session['submitted_text'] = text
            session['submitted_filename'] = filename
            session['success'] = True
            
            return redirect(url_for('index'))
            
        except requests.exceptions.RequestException as e:
            session['error'] = f'Webhook request failed: {str(e)}'
            return redirect(url_for('index'))
    
    except Exception as e:
        session['error'] = f'An error occurred: {str(e)}'
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
