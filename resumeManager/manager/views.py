import json
import os
import re
import requests
import numpy as np
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Resume, JobDescription
from pinecone import Pinecone

# Get webhook URLs from settings
JOB_DESCRIPTION_WEBHOOK_URL = getattr(settings, 'JOB_DESCRIPTION_WEBHOOK_URL', 'https://your-webhook-url.com/job-description')
RESUME_WEBHOOK_URL = getattr(settings, 'RESUME_WEBHOOK_URL', 'https://your-webhook-url.com/resume')
PINECONE_API_KEY = getattr(settings, 'PINECONE_API_KEY', 'your-pinecone-api-key')
PINECONE_INDEX_NAME = getattr(settings, 'PINECONE_INDEX_NAME', 'your-index-name')


@login_required(login_url='login')
@ensure_csrf_cookie
def home(request):
    """Home page - Dashboard"""
    resumes = Resume.objects.all()[:10]  # Get latest 10 resumes for dashboard
    context = {
        'resumes': resumes
    }
    return render(request, 'home.html', context)


@login_required(login_url='login')
def upload_resume(request):
    """Resume upload page"""
    return render(request, 'upload_resume.html')


@login_required(login_url='login')
@require_http_methods(["POST"])
def upload_resume_file(request):
    """
    Handle one or more resume file uploads.
    For each PDF, send to webhook for processing and store metadata.
    """
    if 'resume_file' not in request.FILES and not request.FILES.getlist('resume_file'):
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    files = request.FILES.getlist('resume_file') or [request.FILES['resume_file']]
    results = []
    
    for resume_file in files:
        # Validate file type
        if not resume_file.name.lower().endswith('.pdf'):
            results.append({'file_name': resume_file.name, 'success': False, 'error': 'Only PDF files are allowed'})
            continue
        # Validate file size (10MB)
        if resume_file.size > 10 * 1024 * 1024:
            results.append({'file_name': resume_file.name, 'success': False, 'error': 'File size must be less than 10MB'})
            continue

        try:
            # Step 1: Save resume to database first (this saves file to disk)
            safe_name = resume_file.name
            resume = Resume.objects.create(
                file=resume_file,
                file_name=safe_name,
                status='pending'
            )

            # Step 2: Read file from disk as binary to send to webhook
            webhook_url = RESUME_WEBHOOK_URL

            # If webhook not configured, just save locally as completed with zero score
            if not webhook_url or 'your-webhook-url.com' in webhook_url:
                resume.status = 'completed'
                resume.overall_score = 0
                resume.save()
                results.append({'file_name': safe_name, 'success': True, 'resume_id': resume.id, 'message': 'Saved locally. Configure RESUME_WEBHOOK_URL to enable analysis.'})
                continue
            
            try:
                # Ensure file exists and is accessible
                if not resume.file or not os.path.exists(resume.file.path):
                    resume.status = 'failed'
                    resume.save()
                    results.append({'file_name': safe_name, 'success': False, 'error': 'File was not saved correctly'})
                    continue
                
                # Read the saved file from disk as binary
                with open(resume.file.path, 'rb') as file_on_disk:
                    file_content = file_on_disk.read()
                
                # Prepare file for webhook (send as binary)
                files_payload = {
                    'file': (resume.file_name, file_content, 'application/pdf')
                }
                data_payload = {
                    'resume_id': resume.id,
                    'file_name': resume.file_name
                }
                
                # Send to webhook
                response = requests.post(
                    webhook_url,
                    files=files_payload,
                    data=data_payload,
                    timeout=300  # 5 minute timeout for processing
                )
                
                if response.status_code == 200:
                    # Update resume with analysis results
                    try:
                        analysis_data = response.json()

                        # Sanitize and normalize webhook data before storing
                        normalized = sanitize_webhook_analysis(analysis_data)
                        resume.analysis_data = normalized['analysis_data']
                        resume.overall_score = normalized['overall_score']
                        resume.status = 'completed'
                        resume.save()
                        
                        results.append({'file_name': safe_name, 'success': True, 'resume_id': resume.id, 'message': 'Resume uploaded and analyzed successfully'})
                    except json.JSONDecodeError:
                        resume.status = 'failed'
                        resume.save()
                        results.append({'file_name': safe_name, 'success': False, 'error': 'Invalid response from webhook'})
                else:
                    resume.status = 'failed'
                    resume.save()
                    results.append({'file_name': safe_name, 'success': False, 'error': f'Webhook returned error: {response.status_code}'})
                    
            except requests.exceptions.RequestException as e:
                resume.status = 'failed'
                resume.save()
                results.append({'file_name': safe_name, 'success': False, 'error': f'Failed to connect to webhook: {str(e)}'})

        except Exception as e:
            results.append({'file_name': resume_file.name, 'success': False, 'error': f'Failed to save resume: {str(e)}'})

    # If only one file, keep original shape for backward compatibility
    if len(results) == 1:
        single = results[0]
        if single.get('success'):
            return JsonResponse({'success': True, 'resume_id': single.get('resume_id'), 'message': single.get('message')})
        return JsonResponse({'error': single.get('error')}, status=400)
    return JsonResponse({'results': results})


def sanitize_webhook_analysis(raw):
    """
    Normalize various webhook payload shapes into a consistent structure:
    {
      analysis_data: { candidate_info, skills, experience, education, summary, recommendations, ... },
      overall_score: int
    }
    """
    def safe_int(s, default=0):
        try:
            if isinstance(s, (int, float)):
                return int(s)
            if isinstance(s, str):
                # handle formats like "40/100" or "40"
                if '/' in s:
                    num, denom = s.split('/', 1)
                    num = int(''.join(ch for ch in num if ch.isdigit()))
                    denom = int(''.join(ch for ch in denom if ch.isdigit())) or 100
                    return max(0, min(100, int(round((num / denom) * 100))))
                return int(''.join(ch for ch in s if ch.isdigit()))
        except Exception:
            return default
        return default

    def parse_skill_score(skill_str):
        """Parse skill string like 'React JS (80/100)' to extract name and score"""
        if isinstance(skill_str, dict):
            name = skill_str.get('name', '')
            match = skill_str.get('match')
            if match is not None:
                return {'name': name, 'match': safe_int(match)}
            return {'name': name, 'match': None}
        
        skill_str = str(skill_str)
        # Try to extract score from formats like "React JS (80/100)" or "React JS (80)"
        match = re.search(r'\((\d+)(?:/\d+)?\)', skill_str)
        if match:
            score = safe_int(match.group(1))
            name = re.sub(r'\s*\(\d+(?:/\d+)?\)\s*', '', skill_str).strip()
            return {'name': name, 'match': score}
        return {'name': skill_str, 'match': None}

    # If webhook returns array with one item, unwrap
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]

    # If wrapped with { "output": {...} }
    payload = raw.get('output', raw) if isinstance(raw, dict) else {}

    # Extract fields safely
    candidate_info = payload.get('candidate_info') or {}
    experience = payload.get('candidate_experience') or payload.get('experience') or []
    education = payload.get('candidate_education') or payload.get('education') or []
    skills = payload.get('candidate_skills') or payload.get('skills') or []
    summary = payload.get('candidate_summary') or payload.get('summary') or ''
    recommendations = payload.get('recommendations') or ''
    final_decision = payload.get('final_decision') or {}
    score = safe_int(final_decision.get('final_score') or payload.get('final_score') or payload.get('skill_match_score') or 0)
    
    # Extract additional fields
    languages = payload.get('candidate_languages_known') or payload.get('languages') or []
    projects = payload.get('projects_worked_on') or payload.get('projects') or []
    total_experience = payload.get('cadidate_total_past_experience') or payload.get('candidate_total_past_experience') or payload.get('total_experience') or ''
    why_hire = payload.get('why_hire_candidate') or ''
    why_not_hire = payload.get('why_not_hire_candidate') or ''
    explanation = payload.get('explanation_of_decision') or ''

    # Normalize skills - handle both string format "Skill (80/100)" and object format
    if isinstance(skills, list):
        skills_norm = [parse_skill_score(s) for s in skills]
    else:
        skills_norm = []

    # Normalize experience
    if isinstance(experience, list):
        experience_norm = []
        for item in experience:
            if not isinstance(item, dict):
                continue
            experience_norm.append({
                'title': item.get('role') or item.get('title') or '',
                'company': item.get('place') or item.get('company') or '',
                'duration': item.get('time_period') or item.get('duration') or '',
                'description': item.get('description') or ''
            })
    else:
        experience_norm = []

    # Normalize education - handle both array and single object
    education_norm = []
    if isinstance(education, list):
        for edu in education:
            if isinstance(edu, dict):
                education_norm.append({
                    'degree': edu.get('degree') or '',
                    'university': edu.get('institution') or edu.get('university') or '',
                    'year': edu.get('year_of_graduation') or edu.get('year') or '',
                    'description': ', '.join(edu.get('certifications_and_awards', [])) if isinstance(edu.get('certifications_and_awards'), list) else ''
                })
    elif isinstance(education, dict) and (education.get('degree') or education.get('institution') or education.get('year_of_graduation')):
        education_norm.append({
            'degree': education.get('degree') or '',
            'university': education.get('institution') or education.get('university') or '',
            'year': education.get('year_of_graduation') or education.get('year') or '',
            'description': ''
        })

    # Normalize languages
    languages_norm = []
    if isinstance(languages, list):
        languages_norm = [str(lang) for lang in languages]
    
    # Normalize projects
    projects_norm = []
    if isinstance(projects, list):
        projects_norm = [str(proj) for proj in projects]

    sanitized = {
        'analysis_data': {
            'candidate_info': {
                'name': candidate_info.get('name') or '',
                'email': candidate_info.get('email') or '',
                'phone_number': candidate_info.get('phone_number') or '',
                'linkedin_url': candidate_info.get('linkedin_url') or '',
                'address': candidate_info.get('address') or '',
                'candidate_applied_for': payload.get('candidate_applied_for') or ''
            },
            'summary': summary,
            'skills': skills_norm,
            'experience': experience_norm,
            'education': education_norm,
            'languages': languages_norm,
            'projects': projects_norm,
            'total_experience': total_experience,
            'recommendations': recommendations,
            'why_hire': why_hire,
            'why_not_hire': why_not_hire,
            'explanation': explanation,
            'final_decision': final_decision,
            'needs_human_review': (payload.get('needs_human_review') or '').lower() == 'yes'
        },
        'overall_score': score
    }
    return sanitized


@login_required(login_url='login')
@ensure_csrf_cookie
def analysis(request, resume_id):
    """Resume analysis page"""
    resume = get_object_or_404(Resume, id=resume_id)
    context = {
        'resume_id': resume_id,
        'resume': resume
    }
    return render(request, 'analysis.html', context)


@login_required(login_url='login')
def job_descriptions(request):
    """Job description management page"""
    job_descriptions = JobDescription.objects.all()
    context = {
        'job_descriptions': job_descriptions
    }
    return render(request, 'job_descriptions.html', context)


@require_http_methods(["POST"])
def upload_job_description(request):
    """
    Handle job description file upload
    Sends file to webhook and saves metadata
    """
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title is required'}, status=400)

    job_file = request.FILES['file']
    
    # Validate file type (PDF or text files)
    allowed_extensions = ['.pdf', '.txt', '.doc', '.docx']
    file_ext = os.path.splitext(job_file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return JsonResponse({
            'error': f'Only {", ".join(allowed_extensions)} files are allowed'
        }, status=400)
    
    # Validate file size (10MB)
    if job_file.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'File size must be less than 10MB'}, status=400)

    try:
        # Step 1: Save job description to database first (this saves file to disk)
        job_description = JobDescription.objects.create(
            title=title,
            file=job_file,
            file_name=job_file.name
        )

        # Step 2: Read file from disk as binary to send to webhook
        webhook_url = JOB_DESCRIPTION_WEBHOOK_URL
        
        # Safe guard: if webhook isn't configured, keep the record and return success
        if not webhook_url or 'your-webhook-url.com' in webhook_url:
            return JsonResponse({
                'success': True,
                'job_description_id': job_description.id,
                'message': 'Job description saved locally. Configure JOB_DESCRIPTION_WEBHOOK_URL to enable processing.'
            })
        
        try:
            # Ensure file exists and is accessible
            if not job_description.file or not os.path.exists(job_description.file.path):
                job_description.delete()
                return JsonResponse({
                    'error': 'File was not saved correctly'
                }, status=500)
            
            # Read the saved file from disk as binary
            with open(job_description.file.path, 'rb') as file_on_disk:
                file_content = file_on_disk.read()
            
            # Determine content type
            content_type = job_file.content_type or 'application/octet-stream'
            
            # Prepare file for webhook (send as binary)
            files = {
                'file': (job_description.file_name, file_content, content_type)
            }
            data = {
                'title': title,
                'file_name': job_description.file_name,
                'job_description_id': job_description.id
            }
            
            # Send to webhook
            response = requests.post(
                webhook_url,
                files=files,
                data=data,
                timeout=300  # 5 minute timeout for processing
            )
            
            if response.status_code == 200:
                return JsonResponse({
                    'success': True,
                    'job_description_id': job_description.id,
                    'message': 'Job description uploaded successfully'
                })
            else:
                # Delete the record if webhook fails
                job_description.delete()
                return JsonResponse({
                    'error': f'Webhook returned error: {response.status_code}'
                }, status=500)
                
        except requests.exceptions.RequestException as e:
            # Delete the record if webhook fails
            job_description.delete()
            return JsonResponse({
                'error': f'Failed to connect to webhook: {str(e)}'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to save job description: {str(e)}'
        }, status=500)


@require_http_methods(["DELETE", "POST"])
def delete_job_description(request, job_description_id):
    """
    Delete job description and trigger Pinecone deletion
    Uses file_name as identifier for Pinecone deletion
    """
    job_description = get_object_or_404(JobDescription, id=job_description_id)
    file_name = job_description.file_name
    
    try:
        # Delete from Pinecone using file_name as identifier
        delete_from_pinecone(file_name)
        
        # Delete file from filesystem
        if job_description.file:
            if os.path.isfile(job_description.file.path):
                os.remove(job_description.file.path)
        # Delete database record
        job_description.delete()
        return JsonResponse({
            'success': True,
            'message': 'Job description deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to delete job description: {str(e)}'
        }, status=500)


def delete_from_pinecone(file_name):
    """
    Delete vectors from Pinecone using file_name as identifier
    Uses file-name (with hyphen) as metadata filter key based on provided sample code
    """
    try:
        # Skip if Pinecone is not configured
        if PINECONE_API_KEY == 'your-pinecone-api-key' or PINECONE_INDEX_NAME == 'your-index-name':
            print(f"[DEBUG] Pinecone not configured. Skipping deletion for file: {file_name}")
            return
        
        # Initialize Pinecone client
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Connect to your index
        index = pc.Index(PINECONE_INDEX_NAME)
        
        # Query for vectors with metadata.file-name == file_name
        query_vector = np.zeros(768).tolist()  # Adjust dimension if needed
        
        # Search for vectors with matching file-name metadata
        # Note: Using "file-name" with hyphen as per sample code
        results = index.query(
            vector=query_vector,
            top_k=1000,  # Increase if you expect many chunks
            filter={"file-name": {"$eq": file_name}},
            include_metadata=True
        )
        
        # Delete all vectors found for that file
        if results and results.matches:
            ids_to_delete = [match.id for match in results.matches]
            
            # Delete by ID
            index.delete(ids=ids_to_delete)
            print(f"[DEBUG] Successfully deleted all {len(ids_to_delete)} chunks for '{file_name}'.")
        else:
            print(f"[DEBUG] No vectors found for '{file_name}'. Nothing to delete.")
        
    except ImportError:
        print(f"[DEBUG] Pinecone library not installed. Install with: pip install pinecone-client numpy")
    except Exception as e:
        print(f"[DEBUG] Error deleting from Pinecone: {str(e)}")
        # Don't raise exception - allow deletion to continue even if Pinecone fails
        pass


@require_http_methods(["GET"])
def get_job_descriptions(request):
    """API endpoint to get all job descriptions"""
    job_descriptions = JobDescription.objects.all()
    data = [
        {
            'id': jd.id,
            'title': jd.title,
            'file_name': jd.file_name,
            'upload_date': jd.upload_date.isoformat(),
        }
        for jd in job_descriptions
    ]
    return JsonResponse({'job_descriptions': data})


@require_http_methods(["GET"])
def get_resumes(request):
    """API endpoint to get all resumes"""
    resumes = Resume.objects.all()
    data = []
    for resume in resumes:
        analysis_data = resume.analysis_data or {}
        candidate_info = analysis_data.get('candidate_info', {})
        data.append({
            'id': resume.id,
            'file_name': resume.file_name,
            'upload_date': resume.upload_date.isoformat(),
            'created_at': resume.created_at.isoformat() if hasattr(resume, 'created_at') else resume.upload_date.isoformat(),
            'status': resume.status,
            'overall_score': resume.overall_score,
            'analysis_data': analysis_data,
            'candidate_name': candidate_info.get('name', ''),
            'candidate_email': candidate_info.get('email', ''),
            'candidate_applied_for': candidate_info.get('candidate_applied_for', '') or analysis_data.get('candidate_applied_for', ''),
        })
    return JsonResponse({'resumes': data})


@require_http_methods(["GET"])
def get_resume(request, resume_id):
    """API endpoint to get a single resume"""
    resume = get_object_or_404(Resume, id=resume_id)
    analysis_data = resume.analysis_data or {}
    candidate_info = analysis_data.get('candidate_info', {})
    
    # Generate proper file URL
    file_url = ''
    if resume.file:
        try:
            file_url = request.build_absolute_uri(resume.file.url)
        except Exception:
            file_url = resume.file.url if resume.file else ''
    
    data = {
        'id': resume.id,
        'file_name': resume.file_name,
        'upload_date': resume.upload_date.isoformat(),
        'status': resume.status,
        'overall_score': resume.overall_score,
        'analysis_data': analysis_data,
        'file_url': file_url,
    }
    return JsonResponse(data)


@require_http_methods(["DELETE", "POST"])
def delete_resume(request, resume_id):
    """Delete a resume"""
    resume = get_object_or_404(Resume, id=resume_id)
    
    try:
        # Delete file from filesystem
        if resume.file:
            if os.path.isfile(resume.file.path):
                os.remove(resume.file.path)
        
        # Delete database record
        resume.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Resume deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to delete resume: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def download_resume(request, resume_id):
    """Download resume PDF"""
    from django.http import FileResponse, Http404
    
    resume = get_object_or_404(Resume, id=resume_id)
    
    if not resume.file:
        raise Http404("Resume file not found")
    
    try:
        file_path = resume.file.path
        if not os.path.exists(file_path):
            raise Http404("Resume file not found on disk")
        
        # Open file and create response
        file_handle = open(file_path, 'rb')
        response = FileResponse(file_handle, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{resume.file_name}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Access-Control-Allow-Origin'] = '*'
        return response
    except Http404:
        raise
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to download resume: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def send_email_calendar(request):
    """Send email to candidate and create Google Calendar event"""
    import json
    from datetime import datetime, timedelta
    from urllib.parse import quote
    
    try:
        data = json.loads(request.body)
        resume_id = data.get('resume_id')
        candidate_email = data.get('candidate_email')
        subject = data.get('subject', 'Interview Invitation')
        body = data.get('body', '')
        schedule_calendar = data.get('schedule_calendar', False)
        
        if not candidate_email:
            return JsonResponse({'error': 'Candidate email is required'}, status=400)
        
        # Get resume for candidate info
        resume = get_object_or_404(Resume, id=resume_id)
        analysis_data = resume.analysis_data or {}
        candidate_info = analysis_data.get('candidate_info', {})
        candidate_name = candidate_info.get('name', 'Candidate')
        position = candidate_info.get('candidate_applied_for', '') or analysis_data.get('candidate_applied_for', 'Position')
        
        # Replace placeholders in email body
        email_body = body.replace('{candidate_name}', candidate_name)
        email_body = email_body.replace('{position}', position)
        
        # Create mailto link
        mailto_body = quote(email_body)
        mailto_subject = quote(subject)
        mailto_link = f"mailto:{candidate_email}?subject={mailto_subject}&body={mailto_body}"
        
        # Create Google Calendar link if scheduled
        calendar_link = None
        if schedule_calendar:
            interview_date = data.get('interview_date')
            interview_time = data.get('interview_time')
            duration = data.get('duration', 60)
            location = data.get('location', '')
            
            if interview_date and interview_time:
                # Parse date and time
                dt_str = f"{interview_date}T{interview_time}:00"
                try:
                    dt = datetime.fromisoformat(dt_str)
                    dt_end = dt + timedelta(minutes=duration)
                    
                    # Format for Google Calendar (YYYYMMDDTHHMMSS)
                    start_time = dt.strftime('%Y%m%dT%H%M%S')
                    end_time = dt_end.strftime('%Y%m%dT%H%M%S')
                    
                    # Create Google Calendar URL
                    calendar_title = quote(f"Interview - {candidate_name}")
                    calendar_details = quote(f"Interview for {position}")
                    calendar_location = quote(location) if location else ''
                    
                    calendar_link = (
                        f"https://calendar.google.com/calendar/render?"
                        f"action=TEMPLATE&"
                        f"text={calendar_title}&"
                        f"dates={start_time}/{end_time}&"
                        f"details={calendar_details}&"
                        f"location={calendar_location}"
                    )
                    
                    # Add calendar link to email body
                    email_body += f"\n\nCalendar Event: {calendar_link}"
                except Exception as e:
                    print(f"Error creating calendar link: {e}")
        
        return JsonResponse({
            'success': True,
            'mailto_link': mailto_link,
            'calendar_link': calendar_link,
            'message': 'Email and calendar links generated. Opening email client...'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to process request: {str(e)}'
        }, status=500)


@login_required(login_url='login')
@ensure_csrf_cookie
def email_templates(request):
    """Default email templates management page"""
    from .models import EmailTemplate
    
    templates = EmailTemplate.objects.filter(is_active=True).order_by('-created_at')
    context = {
        'templates': templates
    }
    return render(request, 'email_templates.html', context)


@require_http_methods(["POST"])
def save_email_template(request):
    """Save or update email template"""
    import json
    
    try:
        data = json.loads(request.body)
        template_id = data.get('id')
        subject = data.get('subject', '')
        body = data.get('body', '')
        is_active = data.get('is_active', True)
        
        if not subject or not body:
            return JsonResponse({'error': 'Subject and body are required'}, status=400)
        
        from .models import EmailTemplate
        
        if template_id:
            template = get_object_or_404(EmailTemplate, id=template_id)
            template.subject = subject
            template.body = body
            template.is_active = is_active
        else:
            # Deactivate all other templates if this is set as active
            if is_active:
                EmailTemplate.objects.filter(is_active=True).update(is_active=False)
            template = EmailTemplate.objects.create(
                subject=subject,
                body=body,
                is_active=is_active
            )
        
        template.save()
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'message': 'Template saved successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to save template: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_email_template(request):
    """Get active email template"""
    from .models import EmailTemplate
    
    template = EmailTemplate.objects.filter(is_active=True).first()
    
    if template:
        return JsonResponse({
            'id': template.id,
            'subject': template.subject,
            'body': template.body
        })
    else:
        return JsonResponse({
            'subject': 'Interview Invitation',
            'body': 'Dear {candidate_name},\n\nWe are pleased to invite you for an interview for the position of {position}.\n\nPlease let us know your availability.\n\nBest regards'
        })


@login_required(login_url='login')
@ensure_csrf_cookie
def settings_page(request):
    """Settings page for Google Calendar and Gmail configuration"""
    from .models import GoogleCalendarSettings, GoogleOAuthAppConfig

    # Allow superusers to POST and save global OAuth client credentials
    if request.method == 'POST':
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        client_id = request.POST.get('google_client_id', '').strip()
        client_secret = request.POST.get('google_client_secret', '').strip()
        app_config, _ = GoogleOAuthAppConfig.objects.get_or_create(pk=1)
        app_config.client_id = client_id
        app_config.client_secret = client_secret
        app_config.save()
        return JsonResponse({'success': True, 'message': 'Google OAuth credentials saved'})

    # GET - show current connection status for this user (if logged in) or global
    app_config = GoogleOAuthAppConfig.objects.first()
    if request.user.is_authenticated:
        settings_obj = GoogleCalendarSettings.objects.filter(user=request.user).first()
    else:
        settings_obj = GoogleCalendarSettings.objects.first()

    context = {
        'google_calendar_connected': settings_obj and settings_obj.is_connected,
        'gmail_address': settings_obj.gmail_address if settings_obj else '',
        'app_client_id': app_config.client_id if app_config else '',
        'is_superuser': request.user.is_superuser if hasattr(request, 'user') else False,
    }
    return render(request, 'settings.html', context)


@require_http_methods(["POST"])
def google_calendar_auth(request):
    """Initiate Google Calendar OAuth flow"""
    import secrets
    from django.contrib.sessions.models import Session
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    # Get credentials from DB-config if present, otherwise from settings
    from .models import GoogleOAuthAppConfig
    app_cfg = GoogleOAuthAppConfig.objects.first()
    client_id = app_cfg.client_id if app_cfg and app_cfg.client_id else getattr(settings, 'GOOGLE_CLIENT_ID', None)
    redirect_uri = request.build_absolute_uri('/api/google-calendar/callback/')
    
    if not client_id:
        return JsonResponse({
            'error': 'Google Client ID not configured. Ask an admin to set it on the Settings page.'
        }, status=400)
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.send&"
        f"state={state}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return JsonResponse({'auth_url': auth_url})


@require_http_methods(["GET"])
def google_calendar_callback(request):
    """Handle Google Calendar OAuth callback"""
    from .models import GoogleCalendarSettings
    
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    # Verify state
    session_state = request.session.get('oauth_state')
    if not state or state != session_state:
        return JsonResponse({'error': 'Invalid state parameter'}, status=400)
    
    if not code:
        return JsonResponse({'error': 'No authorization code provided'}, status=400)
    
    try:
        # Exchange code for tokens
        from .models import GoogleOAuthAppConfig
        app_cfg = GoogleOAuthAppConfig.objects.first()
        client_id = app_cfg.client_id if app_cfg and app_cfg.client_id else getattr(settings, 'GOOGLE_CLIENT_ID', None)
        client_secret = app_cfg.client_secret if app_cfg and app_cfg.client_secret else getattr(settings, 'GOOGLE_CLIENT_SECRET', None)
        redirect_uri = request.build_absolute_uri('/api/google-calendar/callback/')

        if not client_id or not client_secret:
            return render(request, 'google_callback.html', {
                'success': False,
                'error': 'Google Client ID or Secret not configured. Ask an admin to set it on the Settings page.'
            })

        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_url, data=token_data, timeout=10)

        if response.status_code != 200:
            return render(request, 'google_callback.html', {
                'success': False,
                'error': 'Failed to get tokens from Google. Check your credentials.'
            })

        tokens = response.json()

        # Get user info
        headers = {'Authorization': f"Bearer {tokens.get('access_token')}"}
        user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
        user_response = requests.get(user_info_url, headers=headers, timeout=10)
        user_info = user_response.json()

        # Save or update settings per-user if possible
        if request.user and request.user.is_authenticated:
            settings_obj, created = GoogleCalendarSettings.objects.get_or_create(user=request.user)
        else:
            settings_obj, created = GoogleCalendarSettings.objects.get_or_create(pk=1)

        settings_obj.google_client_id = client_id
        settings_obj.google_client_secret = client_secret
        # Save refresh token if provided (refresh token present on first consent)
        if tokens.get('refresh_token'):
            settings_obj.google_refresh_token = tokens.get('refresh_token')
        settings_obj.gmail_address = user_info.get('email', '')
        settings_obj.is_connected = True
        settings_obj.save()

        return render(request, 'google_callback.html', {
            'success': True,
            'email': user_info.get('email', '')
        })

    except Exception as e:
        return render(request, 'google_callback.html', {
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
def google_calendar_disconnect(request):
    """Disconnect Google Calendar"""
    from .models import GoogleCalendarSettings

    try:
        if request.user and request.user.is_authenticated:
            settings_obj = GoogleCalendarSettings.objects.filter(user=request.user).first()
        else:
            settings_obj = GoogleCalendarSettings.objects.first()

        if settings_obj:
            settings_obj.google_refresh_token = ''
            settings_obj.gmail_address = ''
            settings_obj.is_connected = False
            settings_obj.save()

        return JsonResponse({'success': True, 'message': 'Disconnected from Google Calendar'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_google_calendar_events(request):
    """Get upcoming events from Google Calendar"""
    from .models import GoogleCalendarSettings
    from datetime import datetime, timedelta
    
    try:
        # Prefer per-user settings when available
        if request.user and request.user.is_authenticated:
            settings_obj = GoogleCalendarSettings.objects.filter(user=request.user).first()
        else:
            settings_obj = GoogleCalendarSettings.objects.first()

        if not settings_obj or not settings_obj.google_refresh_token:
            return JsonResponse({'error': 'Google Calendar not connected'}, status=400)

        # Get client credentials from DB-config or settings
        from .models import GoogleOAuthAppConfig
        app_cfg = GoogleOAuthAppConfig.objects.first()
        client_id = app_cfg.client_id if app_cfg and app_cfg.client_id else getattr(settings, 'GOOGLE_CLIENT_ID', None)
        client_secret = app_cfg.client_secret if app_cfg and app_cfg.client_secret else getattr(settings, 'GOOGLE_CLIENT_SECRET', None)

        if not client_id or not client_secret:
            return JsonResponse({'error': 'Google credentials not configured'}, status=400)

        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': settings_obj.google_refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=token_data, timeout=10)
        tokens = response.json()
        access_token = tokens.get('access_token')
        
        # Get calendar events
        headers = {'Authorization': f"Bearer {access_token}"}
        now = datetime.utcnow().isoformat() + 'Z'
        end_date = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
        
        calendar_url = f"https://www.googleapis.com/calendar/v3/calendars/{settings_obj.calendar_id}/events"
        params = {
            'timeMin': now,
            'timeMax': end_date,
            'maxResults': 50,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        events_response = requests.get(calendar_url, headers=headers, params=params, timeout=10)
        events_data = events_response.json()
        
        events = []
        for event in events_data.get('items', []):
            events.append({
                'id': event.get('id'),
                'title': event.get('summary'),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                'description': event.get('description', ''),
            })
        
        return JsonResponse({'events': events})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@ensure_csrf_cookie
def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            context = {'form': {'non_field_errors': ['Invalid username or password']}}
            return render(request, 'login.html', context, status=401)
    
    return render(request, 'login.html')


@login_required(login_url='login')
def logout_view(request):
    """Logout"""
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def users_management(request):
    """User management page (superuser only)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    return render(request, 'users.html')


@require_http_methods(["GET"])
@login_required(login_url='login')
def get_users(request):
    """Get all users (superuser only)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    users = User.objects.all().values('id', 'username', 'email', 'is_active')
    return JsonResponse({'users': list(users)})


@require_http_methods(["POST"])
@login_required(login_url='login')
def create_user(request):
    """Create a new user (superuser only)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    
    if not username or not password:
        return JsonResponse({'error': 'Username and password are required'}, status=400)
    
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': f'Username "{username}" already exists'}, status=400)
    
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return JsonResponse({
            'success': True,
            'user_id': user.id,
            'message': f'User "{username}" created successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required(login_url='login')
def update_user(request):
    """Update a user (superuser only)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    
    try:
        user = User.objects.get(id=user_id)
        
        if email:
            user.email = email
        
        if password:
            user.set_password(password)
        
        user.save()
        return JsonResponse({'success': True, 'message': 'User updated successfully'})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required(login_url='login')
def delete_user(request):
    """Delete a user (superuser only)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    
    # Prevent deleting the current user
    if int(user_id) == request.user.id:
        return JsonResponse({'error': 'You cannot delete yourself'}, status=400)
    
    try:
        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()
        return JsonResponse({'success': True, 'message': f'User "{username}" deleted successfully'})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
