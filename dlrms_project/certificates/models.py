from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class Certificate(models.Model):
    """Model for storing generated certificates"""
    
    CERTIFICATE_TYPE_CHOICES = [
        ('property_contract', 'Property Contract'),
        ('parcel_certificate', 'Parcel Certificate'),
    ]
    
    CERTIFICATE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    # Certificate Information
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    certificate_number = models.CharField(max_length=50, unique=True)
    certificate_type = models.CharField(max_length=30, choices=CERTIFICATE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=CERTIFICATE_STATUS_CHOICES, default='draft')
    
    # Related Objects
    application = models.OneToOneField('applications.ParcelApplication', on_delete=models.CASCADE, related_name='certificate')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    
    # Certificate Details
    issue_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Document Storage
    pdf_file = models.FileField(upload_to='certificates/pdfs/', null=True, blank=True)
    qr_code = models.ImageField(upload_to='certificates/qr_codes/', null=True, blank=True)
    
    # Security
    document_hash = models.CharField(max_length=256, blank=True, help_text="SHA-256 hash of the PDF")
    blockchain_hash = models.CharField(max_length=256, blank=True, null=True)
    
    # Signatures
    signatures = models.ManyToManyField('signatures.DigitalSignature', blank=True, related_name='certificates')
    
    # Metadata
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_certificates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.certificate_number} - {self.owner.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.generate_certificate_number()
        super().save(*args, **kwargs)
    
    def generate_certificate_number(self):
        """Generate unique certificate number"""
        prefix = "PC" if self.certificate_type == "property_contract" else "PCA"
        year = timezone.now().year
        
        # Find the last certificate of this type for this year
        last_cert = Certificate.objects.filter(
            certificate_number__startswith=f"{prefix}-{year}"
        ).order_by('-id').first()
        
        if last_cert:
            try:
                last_seq = int(last_cert.certificate_number.split('-')[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        
        self.certificate_number = f"{prefix}-{year}-{new_seq:06d}"
    
    def calculate_expiry_date(self):
        """Calculate expiry date based on certificate type"""
        if self.certificate_type == 'property_contract' and self.issue_date:
            self.expiry_date = self.issue_date + timedelta(days=3*365)  # 3 years
        elif self.certificate_type == 'parcel_certificate':
            self.expiry_date = None  # Lifetime validity
    
    @property
    def is_valid(self):
        """Check if certificate is currently valid"""
        if self.status != 'issued':
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            return False
        return True
    
    @property
    def verification_url(self):
        """Get the verification URL for this certificate"""
        from django.conf import settings
        # Use a setting for the base URL or default to a reasonable value
        base_url = getattr(settings, 'CERTIFICATE_VERIFICATION_BASE_URL', 'https://dlrms.cd')
        return f"{base_url}/verify/{self.certificate_id}"
    
    class Meta:
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
        ordering = ['-created_at']


class CertificateTemplate(models.Model):
    """Model for storing certificate templates"""
    
    name = models.CharField(max_length=100)
    certificate_type = models.CharField(max_length=30, choices=Certificate.CERTIFICATE_TYPE_CHOICES, unique=True)
    
    # Template Configuration
    logo_image = models.ImageField(upload_to='certificates/templates/logos/', null=True, blank=True)
    watermark_image = models.ImageField(upload_to='certificates/templates/watermarks/', null=True, blank=True)
    border_image = models.ImageField(upload_to='certificates/templates/borders/', null=True, blank=True)
    
    # Colors (hex format)
    primary_color = models.CharField(max_length=7, default='#000080')  # Navy blue
    secondary_color = models.CharField(max_length=7, default='#FFD700')  # Gold
    text_color = models.CharField(max_length=7, default='#000000')  # Black
    
    # Fonts
    header_font = models.CharField(max_length=50, default='Helvetica-Bold')
    body_font = models.CharField(max_length=50, default='Helvetica')
    
    # Layout Configuration (JSON field for flexibility)
    layout_config = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_certificate_type_display()}"
    
    class Meta:
        verbose_name = "Certificate Template"
        verbose_name_plural = "Certificate Templates"


class CertificateAuditLog(models.Model):
    """Audit log for certificate operations"""
    
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('issued', 'Issued'),
        ('viewed', 'Viewed'),
        ('downloaded', 'Downloaded'),
        ('verified', 'Verified'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.certificate.certificate_number} - {self.action} at {self.timestamp}"
    
    class Meta:
        verbose_name = "Certificate Audit Log"
        verbose_name_plural = "Certificate Audit Logs"
        ordering = ['-timestamp']