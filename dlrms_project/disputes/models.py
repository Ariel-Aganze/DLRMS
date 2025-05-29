from django.db import models
from django.contrib.auth import get_user_model

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
    dispute_number = models.CharField(max_length=50, unique=True)
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
    related_application = models.ForeignKey('applications.TitleApplication', on_delete=models.SET_NULL, blank=True, null=True, related_name='disputes')
    
    # Case Management
    assigned_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_disputes')
    investigation_notes = models.TextField(blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    resolution_date = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    filed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dispute {self.dispute_number} - {self.title}"
    
    class Meta:
        verbose_name = "Dispute"
        verbose_name_plural = "Disputes"
        ordering = ['-filed_at']