from . import views
from django.urls import path

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main pages
    path('', views.home, name='home'),
    path('upload/', views.upload_resume, name='upload_resume'),
    path('analysis/<int:resume_id>/', views.analysis, name='analysis'),
    path('job-descriptions/', views.job_descriptions, name='job_descriptions'),
    path('email-templates/', views.email_templates, name='email_templates'),
    path('settings/', views.settings_page, name='settings'),
    path('users/', views.users_management, name='users_management'),
    
    # API endpoints
    path('api/upload-resume/', views.upload_resume_file, name='upload_resume_file'),
    path('api/upload-job-description/', views.upload_job_description, name='upload_job_description'),
    path('api/job-descriptions/<int:job_description_id>/delete/', views.delete_job_description, name='delete_job_description'),
    path('api/job-descriptions/', views.get_job_descriptions, name='get_job_descriptions'),
    path('api/resumes/', views.get_resumes, name='get_resumes'),
    path('api/resumes/<int:resume_id>/', views.get_resume, name='get_resume'),
    path('api/resumes/<int:resume_id>/delete/', views.delete_resume, name='delete_resume'),
    path('api/resumes/<int:resume_id>/download/', views.download_resume, name='download_resume'),
    path('api/send-email-calendar/', views.send_email_calendar, name='send_email_calendar'),
    path('api/email-templates/', views.save_email_template, name='save_email_template'),
    path('api/email-templates/get/', views.get_email_template, name='get_email_template'),
    path('api/google-calendar/auth/', views.google_calendar_auth, name='google_calendar_auth'),
    path('api/google-calendar/callback/', views.google_calendar_callback, name='google_calendar_callback'),
    path('api/google-calendar/disconnect/', views.google_calendar_disconnect, name='google_calendar_disconnect'),
    path('api/google-calendar/events/', views.get_google_calendar_events, name='get_google_calendar_events'),
    
    # User management API
    path('api/users/', views.get_users, name='get_users'),
    path('api/users/create/', views.create_user, name='create_user'),
    path('api/users/update/', views.update_user, name='update_user'),
    path('api/users/delete/', views.delete_user, name='delete_user'),
]
