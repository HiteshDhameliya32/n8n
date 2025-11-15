from django.contrib import admin
from .models import Resume, JobDescription


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'upload_date', 'status', 'overall_score', 'created_at']
    list_filter = ['status', 'upload_date']
    search_fields = ['file_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_name', 'upload_date', 'created_at']
    list_filter = ['upload_date']
    search_fields = ['title', 'file_name']
    readonly_fields = ['created_at', 'updated_at']
