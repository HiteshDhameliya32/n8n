from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class JobDescription(models.Model):
    """Model for storing job description metadata"""
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='job_descriptions/')
    file_name = models.CharField(max_length=255, help_text="Original file name for Pinecone deletion")
    upload_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Job Description'
        verbose_name_plural = 'Job Descriptions'

    def __str__(self):
        return self.title


class Resume(models.Model):
    """Model for storing resume metadata and analysis results"""
    file = models.FileField(upload_to='resumes/')
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(default=timezone.now)
    
    # Analysis results from webhook (stored as JSON)
    analysis_data = models.JSONField(default=dict, blank=True, null=True)
    overall_score = models.IntegerField(default=0, blank=True, null=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Resume'
        verbose_name_plural = 'Resumes'

    def __str__(self):
        return self.file_name


class EmailTemplate(models.Model):
    """Model for storing default email templates"""
    subject = models.CharField(max_length=255, default='Interview Invitation')
    body = models.TextField(help_text="Use {candidate_name}, {position}, {date}, {time} as placeholders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.subject


class GoogleCalendarSettings(models.Model):
    """Model for storing Google Calendar and Gmail API credentials"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_calendar_settings', null=True, blank=True)
    
    # Google API credentials (encrypted in production)
    google_client_id = models.CharField(max_length=500, blank=True)
    google_client_secret = models.CharField(max_length=500, blank=True)
    google_refresh_token = models.TextField(blank=True, help_text="OAuth refresh token")
    
    # Gmail settings
    gmail_address = models.EmailField(blank=True, help_text="Gmail address for sending emails")
    
    # Calendar settings
    calendar_id = models.CharField(max_length=255, blank=True, default='primary', help_text="Google Calendar ID")
    
    # Status
    is_connected = models.BooleanField(default=False)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Google Calendar Settings'
        verbose_name_plural = 'Google Calendar Settings'
    
    def __str__(self):
        return f"Google Calendar Settings - {self.gmail_address if self.gmail_address else 'Not configured'}"


class GoogleOAuthAppConfig(models.Model):
    """Singleton-like model to hold Google OAuth app credentials for the project.

    This stores the OAuth client id and secret used to perform OAuth flows. Storing
    in the DB allows admins to configure credentials via the UI instead of
    relying only on environment variables. For production, ensure the secret is
    encrypted at rest.
    """
    client_id = models.CharField(max_length=500, blank=True)
    client_secret = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Google OAuth App Config'
        verbose_name_plural = 'Google OAuth App Config'

    def __str__(self):
        display = self.client_id or 'Not configured'
        return f"Google OAuth App - {display}"
