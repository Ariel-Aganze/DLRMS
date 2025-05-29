from django.db import models
from django.contrib.auth import get_user_model
from land_management.models import LandParcel

User = get_user_model()

class TitleApplication(models.Model):
    """Model for land title applications"""
    
    APPLICATION_STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('field_inspection', 'Field Inspection'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('title_issued', 'Title Issued'),
    ]
    
    APPLICATION_TYPE_CHOICES = [
        ('new_registration', 'New Registration'),
        ('title_update', 'Title Update'),
        ('boundary_correction', 'Boundary Correction'),
        ('ownership_verification', 'Ownership Verification'),
    ]
    
    # Basic Information
    application_number = models.CharField(max_length=50, unique=True)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    parcel = models.ForeignKey(LandParcel, on_delete=models.CASCADE, related_name='applications', blank=True, null=True)
    
    # Application Details
    application_type = models.CharField(max_length=30, choices=APPLICATION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='submitted')
    purpose = models.TextField()
    
    # Review Information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_notes = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(blank=True, null=True)
    
    # Approval Information
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_applications')
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Application {self.application_number} - {self.applicant.username}"
    
    class Meta:
        verbose_name = "Title Application"
        verbose_name_plural = "Title Applications"
        ordering = ['-submitted_at']