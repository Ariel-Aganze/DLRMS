from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone

def send_notification_email(notification):
    """
    Send email for a notification
    """
    try:
        # Check if the recipient has an email
        if not notification.recipient.email:
            return False
        
        # Prepare email context
        context = {
            'recipient_name': notification.recipient.get_full_name(),
            'notification': notification,
            'site_name': 'DLRMS',
            'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
            'current_year': timezone.now().year,
        }
        
        # Determine template based on notification type
        template_map = {
            'application_status': 'notifications/emails/application_status.html',
            'transfer_status': 'notifications/emails/transfer_status.html',
            'document_uploaded': 'notifications/emails/document_uploaded.html',
            'approval_required': 'notifications/emails/approval_required.html',
            'deadline_reminder': 'notifications/emails/deadline_reminder.html',
            'system_alert': 'notifications/emails/system_alert.html',
        }
        
        template_name = template_map.get(
            notification.notification_type, 
            'notifications/emails/default_notification.html'
        )
        
        # Render email content
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        # Prepare subject with priority indicator
        priority_prefix = ''
        if notification.priority == 'urgent':
            priority_prefix = '[URGENT] '
        elif notification.priority == 'high':
            priority_prefix = '[IMPORTANT] '
        
        subject = f"{priority_prefix}{notification.title}"
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Update notification
        notification.email_sent = True
        notification.email_sent_at = timezone.now()
        notification.save(update_fields=['email_sent', 'email_sent_at'])
        
        return True
        
    except Exception as e:
        print(f"Error sending email for notification {notification.id}: {str(e)}")
        return False
