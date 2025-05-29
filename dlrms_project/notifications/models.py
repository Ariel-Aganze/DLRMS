from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):
    """Model for system notifications"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('application_status', 'Application Status Update'),
        ('transfer_status', 'Transfer Status Update'),
        ('dispute_update', 'Dispute Update'),
        ('document_uploaded', 'Document Uploaded'),
        ('approval_required', 'Approval Required'),
        ('deadline_reminder', 'Deadline Reminder'),
        ('system_alert', 'System Alert'),
        ('welcome', 'Welcome Message'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic Information
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Related Objects (optional)
    related_application = models.ForeignKey('applications.TitleApplication', on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    related_parcel = models.ForeignKey('land_management.LandParcel', on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    related_dispute = models.ForeignKey('disputes.Dispute', on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    related_transfer = models.ForeignKey('land_management.OwnershipTransfer', on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    
    # Sender Information
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    
    # Email Notification
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']