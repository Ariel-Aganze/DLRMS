from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification
from .utils import send_notification_email

@receiver(post_save, sender=Notification)
def send_email_on_notification_create(sender, instance, created, **kwargs):
    """
    Automatically send email when a notification is created
    """
    if created and not instance.email_sent:
        # Send email asynchronously if you have Celery, otherwise send directly
        send_notification_email(instance)