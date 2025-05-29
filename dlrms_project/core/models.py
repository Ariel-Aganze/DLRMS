from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class AuditLog(models.Model):
    """Model for audit trail and system logging"""
    
    ACTION_TYPE_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('download', 'Download'),
        ('upload', 'Upload'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('transfer', 'Transfer'),
        ('sign', 'Digital Sign'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES)
    description = models.TextField()
    
    # Technical Details
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    session_key = models.CharField(max_length=50, blank=True, null=True)
    
    # Object Information
    object_type = models.CharField(max_length=50, blank=True, null=True, help_text="Model name of the affected object")
    object_id = models.PositiveIntegerField(blank=True, null=True, help_text="ID of the affected object")
    object_repr = models.CharField(max_length=200, blank=True, null=True, help_text="String representation of the object")
    
    # Change Tracking
    old_values = models.JSONField(blank=True, null=True, help_text="Previous values (for updates)")
    new_values = models.JSONField(blank=True, null=True, help_text="New values (for updates)")
    
    # System Information
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action_type} by {self.user} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, user, action_type, description, **kwargs):
        """Helper method to create audit log entries"""
        return cls.objects.create(
            user=user,
            action_type=action_type,
            description=description,
            **kwargs
        )
    
    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']


class SystemSetting(models.Model):
    """Model for system configuration settings"""
    
    SETTING_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]
    
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=10, choices=SETTING_TYPE_CHOICES, default='string')
    description = models.TextField(blank=True, null=True)
    
    # Metadata
    is_public = models.BooleanField(default=False, help_text="Can be accessed by non-admin users")
    is_editable = models.BooleanField(default=True, help_text="Can be modified through admin interface")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
    
    def get_value(self):
        """Get the properly typed value"""
        if self.setting_type == 'integer':
            return int(self.value)
        elif self.setting_type == 'float':
            return float(self.value)
        elif self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.setting_type == 'json':
            return json.loads(self.value)
        return self.value
    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        ordering = ['key']