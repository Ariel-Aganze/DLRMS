# Create this file: dlrms_project/certificates/admin.py

from django.contrib import admin
from .models import Certificate, CertificateTemplate, CertificateAuditLog


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'certificate_type', 'owner', 'status', 'issue_date', 'is_valid']
    list_filter = ['certificate_type', 'status', 'issue_date']
    search_fields = ['certificate_number', 'owner__username', 'owner__first_name', 'owner__last_name']
    readonly_fields = ['certificate_id', 'certificate_number', 'document_hash', 'created_at', 'updated_at']
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('Certificate Information', {
            'fields': ('certificate_id', 'certificate_number', 'certificate_type', 'status')
        }),
        ('Related Objects', {
            'fields': ('application', 'parcel', 'owner')
        }),
        ('Dates', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('Files', {
            'fields': ('pdf_file', 'qr_code')
        }),
        ('Security', {
            'fields': ('document_hash', 'blockchain_hash')
        }),
        ('Metadata', {
            'fields': ('issued_by', 'created_at', 'updated_at')
        })
    )


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'certificate_type', 'is_active', 'created_at']
    list_filter = ['certificate_type', 'is_active']
    search_fields = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'certificate_type', 'is_active')
        }),
        ('Images', {
            'fields': ('logo_image', 'watermark_image', 'border_image')
        }),
        ('Colors', {
            'fields': ('primary_color', 'secondary_color', 'text_color')
        }),
        ('Fonts', {
            'fields': ('header_font', 'body_font')
        }),
        ('Configuration', {
            'fields': ('layout_config',)
        })
    )


@admin.register(CertificateAuditLog)
class CertificateAuditLogAdmin(admin.ModelAdmin):
    list_display = ['certificate', 'action', 'performed_by', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['certificate__certificate_number', 'performed_by__username']
    readonly_fields = ['certificate', 'action', 'performed_by', 'ip_address', 'user_agent', 'details', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False