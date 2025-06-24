from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class Dispute(models.Model):
    """Model for land disputes"""
    
    DISPUTE_STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_investigation', 'Under Investigation'),
        ('mediation', 'In Mediation'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated to Court'),
        ('closed', 'Closed'),
    ]
    
    DISPUTE_TYPE_CHOICES = [
        ('boundary', 'Boundary Dispute'),
        ('ownership', 'Ownership Dispute'),
        ('encroachment', 'Encroachment'),
        ('inheritance', 'Inheritance Dispute'),
        ('fraud', 'Fraudulent Transaction'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic Information
    dispute_number = models.CharField(max_length=50, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    dispute_type = models.CharField(max_length=20, choices=DISPUTE_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='submitted')
    
    # Parties Involved
    complainant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_disputes')
    respondent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_against', blank=True, null=True)
    
    # Related Objects
    parcel = models.ForeignKey('land_management.LandParcel', on_delete=models.CASCADE, related_name='disputes')
    related_application = models.ForeignKey('applications.ParcelApplication', on_delete=models.SET_NULL, blank=True, null=True, related_name='disputes')
    
    # Case Management
    assigned_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_disputes')
    investigation_notes = models.TextField(blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    resolution_date = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    filed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.dispute_number:
            # Generate unique dispute number
            last_dispute = Dispute.objects.order_by('-id').first()
            if last_dispute:
                last_id = int(last_dispute.dispute_number.split('-')[1])
            else:
                last_id = 0
            self.dispute_number = f"DSP-{last_id + 1:06d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Dispute {self.dispute_number} - {self.title}"
    
    class Meta:
        verbose_name = "Dispute"
        verbose_name_plural = "Disputes"
        ordering = ['-filed_at']


class DisputeComment(models.Model):
    """Comments and communications on disputes"""
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal notes only visible to officers
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.dispute.dispute_number}"


class DisputeEvidence(models.Model):
    """Evidence submitted for disputes"""
    EVIDENCE_TYPE_CHOICES = [
        ('document', 'Document'),
        ('photo', 'Photograph'),
        ('witness', 'Witness Statement'),
        ('survey', 'Survey Report'),
        ('other', 'Other'),
    ]
    
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='evidence')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPE_CHOICES)
    file = models.FileField(upload_to='disputes/evidence/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.title} - {self.dispute.dispute_number}"


class DisputeTimeline(models.Model):
    """Timeline events for dispute tracking"""
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='timeline')
    event = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event} - {self.dispute.dispute_number}"


class MediationSession(models.Model):
    """Mediation sessions for disputes"""
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='mediation_sessions')
    scheduled_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    mediator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='mediated_sessions')
    notes = models.TextField(blank=True, null=True)
    outcome = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"Mediation for {self.dispute.dispute_number} on {self.scheduled_date}"