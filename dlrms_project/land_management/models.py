# land_management/models.py
from django.contrib.gis.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

class LandParcel(models.Model):
    """Enhanced model representing a land parcel with document management"""
    
    PARCEL_STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('pending', 'Pending Registration'),
        ('disputed', 'Under Dispute'),
        ('transferred', 'Transfer in Progress'),
    ]
    
    LAND_USE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('agricultural', 'Agricultural'),
        ('industrial', 'Industrial'),
        ('mixed', 'Mixed Use'),
    ]
    
    PROPERTY_TYPE_CHOICES = [
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('land', 'Vacant Land'),
        ('commercial_building', 'Commercial Building'),
        ('industrial_facility', 'Industrial Facility'),
        ('agricultural_land', 'Agricultural Land'),
    ]
    
    # Basic Information
    parcel_id = models.CharField(max_length=50, unique=True)
    title_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='land_parcels')
    
    # Property Information
    property_address = models.TextField()
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPE_CHOICES)
    
    # Location Information
    location = models.CharField(max_length=200)
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    
    # Parcel Details
    size_hectares = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    land_use = models.CharField(max_length=20, choices=LAND_USE_CHOICES)
    status = models.CharField(max_length=20, choices=PARCEL_STATUS_CHOICES, default='pending')
    
    # GIS Fields
    location_point = models.PointField(srid=4326, blank=True, null=True, help_text="GPS coordinates of parcel center")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    
    # Survey Information
    survey_date = models.DateField(blank=True, null=True)
    surveyor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='surveyed_parcels')
    survey_accuracy = models.CharField(max_length=50, blank=True, null=True, help_text="GPS accuracy in meters")
    
    # Registration Information
    registration_date = models.DateTimeField(blank=True, null=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_parcels')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Parcel {self.parcel_id} - {self.owner.username}"
    
    def save(self, *args, **kwargs):
        """Override save to generate parcel_id and update coordinates"""
        if not self.parcel_id:
            self.parcel_id = f"PRC-{uuid.uuid4().hex[:8].upper()}"
        
        # Update location_point from lat/lng if needed
        if self.latitude and self.longitude and not self.location_point:
            from django.contrib.gis.geos import Point
            self.location_point = Point(float(self.longitude), float(self.latitude), srid=4326)
        
        super().save(*args, **kwargs)
    
    @property
    def coordinates(self):
        """Return coordinates as dict"""
        if self.location_point:
            return {
                'lat': self.location_point.y,
                'lng': self.location_point.x
            }
        elif self.latitude and self.longitude:
            return {
                'lat': float(self.latitude),
                'lng': float(self.longitude)
            }
        return None
    
    @property
    def active_document(self):
        """Get the active document for this parcel"""
        # Get the most recent approved certificate first (highest priority)
        certificate = self.parcel_documents.filter(
            document_type='certificate',
            status='approved'
        ).order_by('-issued_date').first()
        
        if certificate:
            return certificate
            
        # If no certificate, get the most recent approved contract
        contract = self.parcel_documents.filter(
            document_type='contract',
            status='approved'
        ).order_by('-issued_date').first()
        
        return contract
    
    @property
    def document_count(self):
        """Count of approved documents for this parcel"""
        return self.parcel_documents.filter(status='approved').count()
    
    class Meta:
        verbose_name = "Land Parcel"
        verbose_name_plural = "Land Parcels"
        ordering = ['-created_at']


class ParcelApplication(models.Model):
    """Model for parcel registration applications"""
    
    APPLICATION_STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('field_inspection', 'Field Inspection'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('document_issued', 'Document Issued'),
    ]
    
    APPLICATION_TYPE_CHOICES = [
        ('contract', 'Property Contract'),
        ('certificate', 'Parcel Certificate'),
    ]
    
    # Basic Information
    application_number = models.CharField(max_length=50, unique=True)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parcel_applications')
    
    # Application Details
    application_type = models.CharField(max_length=20, choices=APPLICATION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='submitted')
    
    # Owner Information
    owner_first_name = models.CharField(max_length=100)
    owner_last_name = models.CharField(max_length=100)
    property_address = models.TextField()
    property_type = models.CharField(max_length=30, choices=LandParcel.PROPERTY_TYPE_CHOICES)
    
    # Document References
    owner_id_document = models.FileField(upload_to='applications/owner_ids/', help_text="Owner's ID document")
    sale_deed_document = models.FileField(upload_to='applications/sale_deeds/', help_text="Sale deed document")
    previous_contract_document = models.FileField(
        upload_to='applications/previous_contracts/', 
        blank=True, 
        null=True,
        help_text="Previous property contract (optional, for certificates only)"
    )
    
    # Related Objects
    parcel = models.ForeignKey(
        LandParcel, 
        on_delete=models.CASCADE, 
        related_name='applications', 
        blank=True, 
        null=True
    )
    
    # Processing Information
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_parcel_applications'
    )
    field_agent = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_field_inspections'
    )
    
    review_notes = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(blank=True, null=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Application {self.application_number} - {self.get_application_type_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to generate application number"""
        if not self.application_number:
            year = timezone.now().year
            count = ParcelApplication.objects.filter(
                submitted_at__year=year
            ).count() + 1
            self.application_number = f"APP-{year}-{count:06d}"
        
        super().save(*args, **kwargs)
    
    @property
    def full_owner_name(self):
        """Return full owner name"""
        return f"{self.owner_first_name} {self.owner_last_name}"
    
    class Meta:
        verbose_name = "Parcel Application"
        verbose_name_plural = "Parcel Applications"
        ordering = ['-submitted_at']


class ParcelDocument(models.Model):
    """Model for parcel documents (contracts and certificates)"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('contract', 'Property Contract'),
        ('certificate', 'Parcel Certificate'),
    ]
    
    DOCUMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('expired', 'Expired'),
        ('superseded', 'Superseded'),
    ]
    
    # Basic Information
    document_number = models.CharField(max_length=50, unique=True)
    parcel = models.ForeignKey(LandParcel, on_delete=models.CASCADE, related_name='parcel_documents')
    application = models.OneToOneField(ParcelApplication, on_delete=models.CASCADE, related_name='issued_document')
    
    # Document Details
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=DOCUMENT_STATUS_CHOICES, default='pending')
    
    # Validity Information
    issued_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField(blank=True, null=True)
    
    # Digital Document
    document_file = models.FileField(upload_to='parcel_documents/', blank=True, null=True)
    document_hash = models.CharField(max_length=256, blank=True, null=True)
    
    # Issuing Authority
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_documents')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.document_number}"
    
    def save(self, *args, **kwargs):
        """Override save to generate document number and set expiration"""
        if not self.document_number:
            year = timezone.now().year
            prefix = "PC" if self.document_type == 'contract' else "CERT"
            count = ParcelDocument.objects.filter(
                document_type=self.document_type,
                issued_date__year=year
            ).count() + 1
            self.document_number = f"{prefix}-{year}-{count:06d}"
        
        # Set expiration date for contracts (3 years)
        if self.document_type == 'contract' and not self.expiration_date:
            self.expiration_date = self.issued_date + timedelta(days=3*365)
        
        super().save(*args, **kwargs)
        
        # If this is an approved certificate, supersede any active contracts
        if (self.document_type == 'certificate' and 
            self.status == 'approved' and 
            self.pk):  # Only for existing records
            
            ParcelDocument.objects.filter(
                parcel=self.parcel,
                document_type='contract',
                status='approved'
            ).update(status='superseded')
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiration_date:
            return timezone.now() > self.expiration_date
        return False
    
    @property
    def is_active(self):
        """Check if document is currently active"""
        return (self.status == 'approved' and 
                not self.is_expired and 
                self.status != 'superseded')
    
    @property
    def days_until_expiration(self):
        """Calculate days until expiration"""
        if self.expiration_date and not self.is_expired:
            delta = self.expiration_date - timezone.now()
            return delta.days
        return None
    
    class Meta:
        verbose_name = "Parcel Document"
        verbose_name_plural = "Parcel Documents"
        ordering = ['-issued_date']


class OwnershipTransfer(models.Model):
    """Enhanced model for land ownership transfers"""
    
    TRANSFER_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TRANSFER_TYPE_CHOICES = [
        ('sale', 'Sale'),
        ('gift', 'Gift'),
        ('inheritance', 'Inheritance'),
        ('exchange', 'Exchange'),
        ('court_order', 'Court Order'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    transfer_number = models.CharField(max_length=50, unique=True)
    parcel = models.ForeignKey(LandParcel, on_delete=models.CASCADE, related_name='ownership_transfers')
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='initiated')
    
    # Parties
    current_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers_as_current_owner')
    new_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers_as_new_owner')
    
    # Transfer Details
    transfer_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, help_text="Transfer value in Francs")
    conditions = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Legal Requirements
    legal_document_required = models.BooleanField(default=True)
    notary_required = models.BooleanField(default=True)
    court_approval_required = models.BooleanField(default=False)
    
    # Processing
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_transfers')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transfers')
    approval_date = models.DateTimeField(blank=True, null=True)
    completion_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Transfer {self.transfer_number} - {self.current_owner} to {self.new_owner}"
    
    def save(self, *args, **kwargs):
        """Override save to generate transfer number"""
        if not self.transfer_number:
            year = timezone.now().year
            count = OwnershipTransfer.objects.filter(
                initiated_at__year=year
            ).count() + 1
            self.transfer_number = f"TRF-{year}-{count:06d}"
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Ownership Transfer"
        verbose_name_plural = "Ownership Transfers"
        ordering = ['-initiated_at']