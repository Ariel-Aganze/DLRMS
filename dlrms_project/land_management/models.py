from django.contrib.gis.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class LandParcel(models.Model):
    """Model representing a land parcel with basic GIS support"""
    
    PARCEL_STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('pending', 'Pending Registration'),
        ('disputed', 'Under Dispute'),
        ('transferred', 'Transfer in Progress'),
    ]
    
    PROPERTY_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('agricultural', 'Agricultural'),
        ('industrial', 'Industrial'),
        ('mixed', 'Mixed Use'),
    ]
    
    # Basic Information
    parcel_id = models.CharField(max_length=50, unique=True)
    title_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='land_parcels')
    
    # Location Information
    location = models.CharField(max_length=200)  # Property address
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    
    # Parcel Details
    size_hectares = models.DecimalField(max_digits=10, decimal_places=4)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES, default='residential')
    status = models.CharField(max_length=20, choices=PARCEL_STATUS_CHOICES, default='pending')
    
    # GIS Fields - Simple PostGIS integration
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    
    # Registration Information
    registration_date = models.DateTimeField(blank=True, null=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_parcels')
    
    # Active title tracking
    active_title_type = models.CharField(max_length=30, blank=True, null=True, 
                                         choices=[
                                             ('property_contract', 'Property Contract'),
                                             ('parcel_certificate', 'Parcel Certificate'),
                                         ])
    active_title_expiry = models.DateField(blank=True, null=True)  # For Property Contracts
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Parcel {self.parcel_id} - {self.owner.username}"
    
    def save(self, *args, **kwargs):
        if not self.parcel_id:
            # Generate a unique parcel ID
            last_parcel = LandParcel.objects.order_by('-id').first()
            if last_parcel:
                last_id = last_parcel.id
            else:
                last_id = 0
            self.parcel_id = f"PAR-{last_id + 1:06d}"
        
        super().save(*args, **kwargs)
    
    def get_active_title(self):
        """Returns the active title for this parcel"""
        from applications.models import ParcelTitle
        return ParcelTitle.objects.filter(parcel=self, is_active=True).first()
    
    @property
    def coordinates(self):
        """Return coordinates as dict"""
        if self.latitude and self.longitude:
            return {
                'lat': float(self.latitude),
                'lng': float(self.longitude)
            }
        return None
    
    class Meta:
        verbose_name = "Land Parcel"
        verbose_name_plural = "Land Parcels"
        ordering = ['-created_at']

class OwnershipTransfer(models.Model):
    """Model for tracking land ownership transfers"""
    
    TRANSFER_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('awaiting_receiver', 'Awaiting Receiver Confirmation'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('canceled', 'Canceled'),
    ]
    
    TRANSFER_REASON_CHOICES = [
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
    title = models.ForeignKey('applications.ParcelTitle', on_delete=models.CASCADE, related_name='transfers')
    
    # Transfer Parties
    current_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers_as_seller')
    new_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers_as_buyer')
    
    # Transfer Details
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS_CHOICES, default='initiated')
    reason = models.CharField(max_length=20, choices=TRANSFER_REASON_CHOICES)
    other_reason = models.CharField(max_length=200, blank=True, null=True)
    
    # Financial Information (optional, for tracking purposes)
    transfer_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    # Documents
    sale_deed = models.FileField(upload_to='transfers/sale_deeds/', blank=True, null=True)
    current_owner_id_document = models.FileField(upload_to='transfers/owner_ids/', blank=True, null=True)
    new_owner_id_document = models.FileField(upload_to='transfers/buyer_ids/', blank=True, null=True)
    transfer_certificate = models.FileField(upload_to='transfers/certificates/', blank=True, null=True)
    
    # Receiver Details (stored when entered)
    receiver_national_id = models.CharField(max_length=50)
    receiver_first_name = models.CharField(max_length=100)
    receiver_last_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=20)
    receiver_email = models.EmailField()
    
    # Review Information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='reviewed_transfers')
    review_date = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    receiver_confirmed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Deadline tracking
    receiver_deadline = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Transfer {self.transfer_number}: {self.current_owner} to {self.new_owner}"
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            # Generate unique transfer number
            import uuid
            from datetime import datetime
            self.transfer_number = f"TRF-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Set receiver deadline (3 days from initiation)
        if not self.receiver_deadline and self.status == 'initiated':
            from datetime import timedelta
            from django.utils import timezone
            self.receiver_deadline = timezone.now() + timedelta(days=3)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if receiver confirmation deadline has passed"""
        if self.receiver_deadline and self.status == 'awaiting_receiver':
            from django.utils import timezone
            return timezone.now() > self.receiver_deadline
        return False
    
    class Meta:
        verbose_name = "Ownership Transfer"
        verbose_name_plural = "Ownership Transfers"
        ordering = ['-initiated_at']


class ParcelBoundary(models.Model):
    """Model for storing polygon boundary data for land parcels"""
    application = models.OneToOneField('applications.ParcelApplication', on_delete=models.CASCADE, related_name='boundary')
    polygon_geojson = models.TextField(help_text="GeoJSON representation of the polygon boundary")
    center_lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    center_lng = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    area_sqm = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Area in square meters")
    area_hectares = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, help_text="Area in hectares")
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_boundaries')
    updated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_boundaries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Boundary for Application {self.application.application_number}"
    
    class Meta:
        verbose_name = "Parcel Boundary"
        verbose_name_plural = "Parcel Boundaries"