from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from notifications.models import Notification
from .models import ParcelApplication, ParcelDocument

@receiver(post_save, sender=ParcelApplication)
def handle_application_submission(sender, instance, created, **kwargs):
    """Handle new application submission"""
    if created:
        # Create notification for registrars
        from accounts.models import User
        registrars = User.objects.filter(role__in=['registry_officer', 'admin'])
        
        for registrar in registrars:
            Notification.objects.create(
                recipient=registrar,
                title='New Parcel Application Submitted',
                message=f'Application {instance.application_number} for {instance.get_application_type_display()} has been submitted by {instance.applicant.get_full_name()}.',
                notification_type='application_status',
                related_application=instance
            )
    
    elif instance.status in ['approved', 'rejected']:
        # Notify applicant of status change
        Notification.objects.create(
            recipient=instance.applicant,
            title=f'Application {instance.status.title()}',
            message=f'Your {instance.get_application_type_display()} application ({instance.application_number}) has been {instance.status}.',
            notification_type='application_status',
            related_application=instance
        )

@receiver(post_save, sender=ParcelDocument)
def handle_document_issuance(sender, instance, created, **kwargs):
    """Handle document issuance"""
    if created and instance.status == 'approved':
        # Notify parcel owner
        Notification.objects.create(
            recipient=instance.parcel.owner,
            title='Document Issued',
            message=f'Your {instance.get_document_type_display()} for parcel {instance.parcel.parcel_id} has been issued successfully.',
            notification_type='document_uploaded',
            related_parcel=instance.parcel
        )