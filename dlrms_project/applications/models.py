# File: applications/models.py (Updated with fixes)
from django.db import models
from django.contrib.auth import get_user_model
from land_management.models import LandParcel
import uuid
from datetime import datetime

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

class ParcelApplication(models.Model):
    """Model for parcel registration applications"""
    
    APPLICATION_STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('field_inspection', 'Field Inspection'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    APPLICATION_TYPE_CHOICES = [
        ('property_contract', 'Property Contract'),
        ('parcel_certificate', 'Parcel Certificate'),
    ]
    
    # Basic Information
    application_number = models.CharField(max_length=50, unique=True, blank=True)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parcel_applications')
    
    # Application Details
    owner_first_name = models.CharField(max_length=100)
    owner_last_name = models.CharField(max_length=100)
    property_address = models.CharField(max_length=255)
    property_type = models.CharField(max_length=100)
    application_type = models.CharField(max_length=30, choices=APPLICATION_TYPE_CHOICES)
    
    # Status and Processing
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='submitted')
    field_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_applications')
    
    # Review Information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_parcel_applications')
    review_notes = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Application {self.application_number} - {self.applicant.username}"
    
    def save(self, *args, **kwargs):
        if not self.application_number:
            # Generate a unique application number
            prefix = "PC" if self.application_type == "property_contract" else "PCA"
            year = datetime.now().year
            
            # Find the last application for this year and type
            last_application = ParcelApplication.objects.filter(
                application_number__startswith=f"{prefix}-{year}"
            ).order_by('-id').first()
            
            if last_application:
                # Extract the sequential number from the last application
                try:
                    last_seq = int(last_application.application_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (ValueError, IndexError):
                    new_seq = 1
            else:
                new_seq = 1
            
            self.application_number = f"{prefix}-{year}-{new_seq:06d}"
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Parcel Application"
        verbose_name_plural = "Parcel Applications"
        ordering = ['-submitted_at']


class ParcelDocument(models.Model):
    """Model for documents uploaded with parcel applications"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('owner_id', 'Owner ID'),
        ('sale_deed', 'Sale Deed'),
        ('previous_contract', 'Previous Property Contract'),
    ]
    
    application = models.ForeignKey(ParcelApplication, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='parcel_applications/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_document_type_display()} for {self.application.application_number}"
    
    class Meta:
        verbose_name = "Parcel Document"
        verbose_name_plural = "Parcel Documents"


class ParcelTitle(models.Model):
    """Model for parcel titles (Property Contract or Parcel Certificate)"""
    
    TITLE_TYPE_CHOICES = [
        ('property_contract', 'Property Contract'),
        ('parcel_certificate', 'Parcel Certificate'),
    ]
    
    title_number = models.CharField(max_length=50, unique=True, blank=True)
    parcel = models.ForeignKey('land_management.LandParcel', on_delete=models.CASCADE, related_name='titles')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parcel_titles')
    title_type = models.CharField(max_length=30, choices=TITLE_TYPE_CHOICES)
    issue_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)  # Null for Parcel Certificate (lifetime validity)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.get_title_type_display()} - {self.title_number}"
    
    def save(self, *args, **kwargs):
        if not self.title_number:
            # Generate a unique title number
            prefix = "PCT" if self.title_type == "property_contract" else "PCA"
            year = datetime.now().year
            
            # Find the last title for this year and type
            last_title = ParcelTitle.objects.filter(
                title_number__startswith=f"{prefix}-{year}"
            ).order_by('-id').first()
            
            if last_title:
                try:
                    last_seq = int(last_title.title_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (ValueError, IndexError):
                    new_seq = 1
            else:
                new_seq = 1
            
            self.title_number = f"{prefix}-{year}-{new_seq:06d}"
            
        # Set expiry date for Property Contract (3 years from issue date)
        if self.title_type == 'property_contract' and not self.expiry_date:
            from datetime import date, timedelta
            self.expiry_date = date.today() + timedelta(days=3*365)  # 3 years
            
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Parcel Title"
        verbose_name_plural = "Parcel Titles"