import os
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

def get_upload_path(instance, filename):
    """Generate upload path for documents"""
    return f"documents/{instance.document_type}/{filename}"

class Document(models.Model):
    """Model for storing documents"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('identity', 'Identity Document'),
        ('proof_of_ownership', 'Proof of Ownership'),
        ('survey_map', 'Survey Map'),
        ('legal_document', 'Legal Document'),
        ('transfer_agreement', 'Transfer Agreement'),
        ('dispute_evidence', 'Dispute Evidence'),
        ('title_deed', 'Title Deed'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to=get_upload_path)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    # Relationships
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    
    # Related Objects (we'll use generic foreign keys later for flexibility)
    related_application = models.ForeignKey('applications.TitleApplication', on_delete=models.CASCADE, blank=True, null=True, related_name='documents')
    related_parcel = models.ForeignKey('land_management.LandParcel', on_delete=models.CASCADE, blank=True, null=True, related_name='documents')
    related_dispute = models.ForeignKey('disputes.Dispute', on_delete=models.CASCADE, blank=True, null=True, related_name='documents')
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    verification_date = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.document_type}"
    
    @property
    def file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()
    
    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ['-uploaded_at']