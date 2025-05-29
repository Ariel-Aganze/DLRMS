from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class DigitalSignature(models.Model):
    """Model for digital signatures"""
    
    SIGNATURE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('signed', 'Signed'),
        ('invalid', 'Invalid'),
        ('revoked', 'Revoked'),
    ]
    
    DOCUMENT_TYPE_CHOICES = [
        ('title_deed', 'Title Deed'),
        ('transfer_agreement', 'Transfer Agreement'),
        ('application_approval', 'Application Approval'),
        ('dispute_resolution', 'Dispute Resolution'),
        ('legal_document', 'Legal Document'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    signature_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    signer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='digital_signatures')
    document_hash = models.CharField(max_length=256, help_text="SHA-256 hash of the document")
    signature_hash = models.CharField(max_length=512, help_text="Digital signature hash")
    
    # Document Information
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    document_title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=SIGNATURE_STATUS_CHOICES, default='pending')
    
    # Related Objects
    related_application = models.ForeignKey('applications.TitleApplication', on_delete=models.SET_NULL, blank=True, null=True, related_name='signatures')
    related_parcel = models.ForeignKey('land_management.LandParcel', on_delete=models.SET_NULL, blank=True, null=True, related_name='signatures')
    related_transfer = models.ForeignKey('land_management.OwnershipTransfer', on_delete=models.SET_NULL, blank=True, null=True, related_name='signatures')
    related_document = models.ForeignKey('documents.Document', on_delete=models.SET_NULL, blank=True, null=True, related_name='signatures')
    
    # Certificate Information
    certificate_serial = models.CharField(max_length=100, blank=True, null=True)
    certificate_issuer = models.CharField(max_length=200, blank=True, null=True)
    certificate_valid_from = models.DateTimeField(blank=True, null=True)
    certificate_valid_until = models.DateTimeField(blank=True, null=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=100, blank=True, null=True)
    verification_timestamp = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    signed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Signature by {self.signer.username} for {self.document_title}"
    
    class Meta:
        verbose_name = "Digital Signature"
        verbose_name_plural = "Digital Signatures"
        ordering = ['-signed_at']