from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.files.base import ContentFile

from applications.models import ParcelApplication
from .models import Certificate, CertificateAuditLog
from .generator import CertificateGenerator


@receiver(post_save, sender=ParcelApplication)
def generate_certificate_on_approval(sender, instance, **kwargs):
    """Automatically generate certificate when application is approved"""
    
    # Check if status changed to approved
    if instance.status == 'approved' and not hasattr(instance, 'certificate'):
        try:
            # Create certificate record
            certificate = Certificate.objects.create(
                application=instance,
                parcel=instance.parcel,
                owner=instance.applicant,
                certificate_type=instance.application_type,
                issued_by=instance.reviewed_by,
                issue_date=timezone.now()
            )
            
            # Calculate expiry date
            certificate.calculate_expiry_date()
            
            # Generate PDF
            generator = CertificateGenerator()
            try:
                pdf_content, document_hash = generator.generate_certificate(certificate)
                
                # Save PDF file
                certificate.pdf_file.save(
                    f'certificate_{certificate.certificate_number}.pdf',
                    ContentFile(pdf_content)
                )
                
                # Save document hash
                certificate.document_hash = document_hash
                certificate.status = 'issued'
                certificate.save()
                
                # Create audit log
                CertificateAuditLog.objects.create(
                    certificate=certificate,
                    action='created',
                    performed_by=instance.reviewed_by,
                    details={
                        'auto_generated': True,
                        'trigger': 'application_approval'
                    }
                )
            except Exception as e:
                # If PDF generation fails, still keep the certificate record
                print(f"Error generating PDF for certificate: {str(e)}")
                certificate.status = 'draft'
                certificate.save()
            
        except Exception as e:
            # Log the error but don't stop the approval process
            print(f"Error generating certificate: {str(e)}")