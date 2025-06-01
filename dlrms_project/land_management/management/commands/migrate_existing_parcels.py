from django.core.management.base import BaseCommand
from django.utils import timezone
from land_management.models import LandParcel, ParcelDocument
from applications.models import TitleApplication

class Command(BaseCommand):
    help = 'Migrate existing land parcels to new structure'

    def handle(self, *args, **options):
        """Migrate existing data to new structure"""
        
        # Get existing parcels without documents
        parcels_without_docs = LandParcel.objects.filter(
            parcel_documents__isnull=True
        ).distinct()
        
        created_docs = 0
        for parcel in parcels_without_docs:
            # Try to find related application
            related_app = TitleApplication.objects.filter(
                parcel=parcel,
                status='approved'
            ).first()
            
            if related_app:
                # Create document based on application
                doc_type = 'certificate' if 'certificate' in related_app.purpose.lower() else 'contract'
                
                document = ParcelDocument.objects.create(
                    parcel=parcel,
                    document_type=doc_type,
                    status='approved',
                    issued_date=related_app.approval_date or timezone.now(),
                    issued_by=related_app.approved_by
                )
                created_docs += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'Created {doc_type} for parcel {parcel.parcel_id}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_docs} documents')
        )
        