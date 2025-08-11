# In dlrms_project/disputes/models.py
# Add these new choices and fields to the Dispute model

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
    
    # ADD THIS NEW CHOICE SET
    RESOLUTION_APPROACH_CHOICES = [
        ('direct_mediation', 'Direct Mediation - Face-to-face discussion'),
        ('shuttle_mediation', 'Shuttle Mediation - Separate meetings'),
        ('technical_investigation', 'Technical Investigation - Survey/documentation'),
        ('documentary_review', 'Documentary Review - Legal documents focus'),
        ('site_inspection', 'Site Inspection - Physical verification'),
        ('multi_party_conference', 'Multi-Party Conference - Multiple stakeholders'),
        ('traditional_resolution', 'Traditional Resolution - Local leaders involvement'),
        ('fast_track', 'Fast Track - Quick resolution for simple cases'),
        ('complex_investigation', 'Complex Investigation - Extensive research required'),
    ]
    
    # Basic Information (existing fields)
    dispute_number = models.CharField(max_length=50, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    dispute_type = models.CharField(max_length=20, choices=DISPUTE_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='submitted')
    
    # Parties Involved (existing fields)
    complainant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_disputes')
    respondent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputes_against')
    respondent_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Related Land (existing fields)
    parcel = models.ForeignKey('land_management.LandParcel', on_delete=models.SET_NULL, null=True, blank=True)
    related_application = models.ForeignKey('applications.ParcelApplication', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Case Management (existing fields)
    assigned_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_disputes')
    investigation_notes = models.TextField(blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    resolution_date = models.DateTimeField(null=True, blank=True)
    
    # ADD THESE NEW FIELDS FOR RESOLUTION APPROACH
    suggested_approach = models.CharField(
        max_length=30, 
        choices=RESOLUTION_APPROACH_CHOICES, 
        blank=True, 
        null=True,
        help_text="Recommended approach for resolving this dispute"
    )
    approach_notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Additional guidance for the assigned officer"
    )
    approach_suggested_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='suggested_approaches'
    )
    approach_suggested_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps (existing fields)
    filed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.dispute_number:
            # Generate unique dispute number
            prefix = 'DSP'
            year = timezone.now().year
            last_dispute = Dispute.objects.filter(
                dispute_number__startswith=f'{prefix}{year}'
            ).order_by('dispute_number').last()
            
            if last_dispute:
                last_number = int(last_dispute.dispute_number[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.dispute_number = f'{prefix}{year}{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Dispute {self.dispute_number} - {self.title}"
    
    class Meta:
        verbose_name = "Dispute"
        verbose_name_plural = "Disputes"
        ordering = ['-filed_at']


# ADD THIS NEW MODEL FOR TRACKING APPROACH EFFECTIVENESS
class ApproachEffectiveness(models.Model):
    """Track which approaches work best for different dispute types"""
    dispute_type = models.CharField(max_length=20, choices=Dispute.DISPUTE_TYPE_CHOICES)
    approach = models.CharField(max_length=30, choices=Dispute.RESOLUTION_APPROACH_CHOICES)
    success_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0)
    average_resolution_days = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def success_rate(self):
        if self.total_count == 0:
            return 0
        return (self.success_count / self.total_count) * 100
    
    class Meta:
        unique_together = ['dispute_type', 'approach']
        verbose_name = "Approach Effectiveness"
        verbose_name_plural = "Approach Effectiveness Records"
    
    def __str__(self):
        return f"{self.get_dispute_type_display()} - {self.get_approach_display()}: {self.success_rate:.1f}%"


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