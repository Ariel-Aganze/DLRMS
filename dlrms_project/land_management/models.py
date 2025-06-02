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
    """Model for land ownership transfers"""
    
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
    
    class Meta:
        verbose_name = "Ownership Transfer"
        verbose_name_plural = "Ownership Transfers"
        ordering = ['-initiated_at']