from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

class Command(BaseCommand):
    help = 'Test email notification system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address to send test notification to',
        )
        parser.add_argument(
            '--type',
            type=str,
            default='system_alert',
            choices=['system_alert', 'application_status', 'document_uploaded', 
                    'approval_required', 'transfer_status', 'deadline_reminder'],
            help='Type of notification to test',
        )
    
    def handle(self, *args, **options):
        email = options['email']
        notification_type = options['type']
        
        # Try to find user with this email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'No user found with email: {email}')
            )
            return
        
        # Create test notification
        notification = Notification.objects.create(
            recipient=user,
            title=f'Test {notification_type.replace("_", " ").title()} Notification',
            message='This is a test notification to verify that email notifications are working correctly.',
            notification_type=notification_type,
            priority='high' if notification_type in ['approval_required', 'deadline_reminder'] else 'normal',
            sender=None
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Test notification created and email sent to {email}'
            )
        )