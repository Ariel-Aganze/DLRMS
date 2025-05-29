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
    
    LAND_USE_CHOICES = [
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
    location = models.CharField(max_length=200)
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    
    # Parcel Details
    size_hectares = models.DecimalField(max_digits=10, decimal_places=4)
    land_use = models.CharField(max_length=20, choices=LAND_USE_CHOICES)
    status = models.CharField(max_length=20, choices=PARCEL_STATUS_CHOICES, default='pending')
    
    # Basic GIS Fields - Simple PostGIS integration
    # Point geometry for parcel center/reference point
    location_point = models.PointField(srid=4326, blank=True, null=True, help_text="GPS coordinates of parcel center")
    
    # Legacy coordinate fields (kept for backward compatibility)
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
        """Override save to update calculated fields"""
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