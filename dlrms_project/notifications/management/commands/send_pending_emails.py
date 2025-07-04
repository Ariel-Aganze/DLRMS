from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification
from notifications.utils import send_notification_email

class Command(BaseCommand):
    help = 'Send pending email notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry sending failed email notifications',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to look back for unsent emails (default: 24)',
        )
    
    def handle(self, *args, **options):
        # Get notifications that haven't been sent via email
        cutoff_time = timezone.now() - timedelta(hours=options['hours'])
        
        notifications = Notification.objects.filter(
            email_sent=False,
            created_at__gte=cutoff_time
        ).select_related('recipient')
        
        if options['retry_failed']:
            self.stdout.write(f'Found {notifications.count()} unsent email notifications')
        
        success_count = 0
        failure_count = 0
        
        for notification in notifications:
            if send_notification_email(notification):
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sent email to {notification.recipient.email} for notification {notification.id}'
                    )
                )
            else:
                failure_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to send email to {notification.recipient.email} for notification {notification.id}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nEmail sending complete: {success_count} sent, {failure_count} failed'
            )
        )