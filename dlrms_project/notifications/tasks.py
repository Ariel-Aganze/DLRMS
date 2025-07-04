# Optional: Use Celery for asynchronous email sending

# from celery import shared_task
# from .models import Notification
# from .utils import send_notification_email

# @shared_task
# def send_notification_email_async(notification_id):
#     """
#     Asynchronously send email for a notification
#     """
#     try:
#         notification = Notification.objects.get(id=notification_id)
#         return send_notification_email(notification)
#     except Notification.DoesNotExist:
#         return False


# File: Update notifications/signals.py for async sending
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.conf import settings
# from .models import Notification
# from .utils import send_notification_email

# @receiver(post_save, sender=Notification)
# def send_email_on_notification_create(sender, instance, created, **kwargs):
#     """
#     Automatically send email when a notification is created
#     """
#     if created and not instance.email_sent:
#         # Check if Celery is configured
#         if hasattr(settings, 'CELERY_BROKER_URL') and settings.CELERY_BROKER_URL:
#             from .tasks import send_notification_email_async
#             send_notification_email_async.delay(instance.id)
#         else:
#             # Send synchronously
#             send_notification_email(instance)

# pip install celery redis
# CELERY_BROKER_URL = 'redis://localhost:6379'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379'