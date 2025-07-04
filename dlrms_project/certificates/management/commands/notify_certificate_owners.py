from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from certificates.models import Certificate, CertificateAuditLog
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Send notifications to landowners about their certificates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--notify-undownloaded',
            action='store_true',
            help='Notify owners who have not downloaded their certificates',
        )
        parser.add_argument(
            '--notify-expiring',
            action='store_true',
            help='Notify owners whose certificates are expiring soon',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to check for expiring certificates (default: 30)',
        )
    
    def handle(self, *args, **options):
        if options['notify_undownloaded']:
            self.notify_undownloaded_certificates()
        
        if options['notify_expiring']:
            self.notify_expiring_certificates(options['days'])
        
        if not options['notify_undownloaded'] and not options['notify_expiring']:
            self.stdout.write(
                self.style.WARNING('No action specified. Use --notify-undownloaded or --notify-expiring')
            )
    
    def notify_undownloaded_certificates(self):
        """Notify owners who haven't downloaded their certificates"""
        self.stdout.write('Checking for undownloaded certificates...')
        
        # Get all issued certificates
        certificates = Certificate.objects.filter(status='issued')
        
        notified_count = 0
        for certificate in certificates:
            # Check if owner has downloaded the certificate
            owner_downloads = CertificateAuditLog.objects.filter(
                certificate=certificate,
                action='downloaded',
                performed_by=certificate.owner
            ).exists()
            
            if not owner_downloads:
                # Check if we've already sent a notification about this
                existing_notification = Notification.objects.filter(
                    recipient=certificate.owner,
                    title__contains='Certificate Ready',
                    message__contains=certificate.certificate_number
                ).exists()
                
                if not existing_notification:
                    # Send notification
                    Notification.objects.create(
                        recipient=certificate.owner,
                        title='Certificate Ready for Download',
                        message=f'Your {certificate.get_certificate_type_display()} certificate {certificate.certificate_number} is ready for download. Please log in to download it.',
                        notification_type='document_uploaded',
                        priority='high'
                    )
                    notified_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Notified {certificate.owner.get_full_name()} about certificate {certificate.certificate_number}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Sent {notified_count} notifications for undownloaded certificates')
        )
    
    def notify_expiring_certificates(self, days):
        """Notify owners whose certificates are expiring soon"""
        self.stdout.write(f'Checking for certificates expiring within {days} days...')
        
        # Calculate the date range
        today = timezone.now().date()
        expiry_threshold = today + timedelta(days=days)
        
        # Get certificates that are expiring soon
        expiring_certificates = Certificate.objects.filter(
            status='issued',
            expiry_date__isnull=False,
            expiry_date__date__lte=expiry_threshold,
            expiry_date__date__gt=today  # Not already expired
        )
        
        notified_count = 0
        for certificate in expiring_certificates:
            days_until_expiry = (certificate.expiry_date.date() - today).days
            
            # Check if we've already sent a notification recently (within last 7 days)
            recent_notification = Notification.objects.filter(
                recipient=certificate.owner,
                title__contains='Certificate Expiring',
                message__contains=certificate.certificate_number,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()
            
            if not recent_notification:
                # Send notification
                Notification.objects.create(
                    recipient=certificate.owner,
                    title='Certificate Expiring Soon',
                    message=f'Your {certificate.get_certificate_type_display()} certificate {certificate.certificate_number} will expire in {days_until_expiry} days on {certificate.expiry_date.strftime("%B %d, %Y")}. Please renew it before expiration.',
                    notification_type='deadline_reminder',
                    priority='urgent' if days_until_expiry <= 7 else 'high'
                )
                notified_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Notified {certificate.owner.get_full_name()} about expiring certificate {certificate.certificate_number} (expires in {days_until_expiry} days)'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Sent {notified_count} notifications for expiring certificates')
        )