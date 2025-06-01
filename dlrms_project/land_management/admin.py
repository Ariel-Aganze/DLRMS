from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import LandParcel, ParcelApplication, ParcelDocument, OwnershipTransfer

@admin.register(LandParcel)
class LandParcelAdmin(admin.ModelAdmin):
    list_display = [
        'parcel_id', 
        'owner_name', 
        'property_type', 
        'property_address_short', 
        'status', 
        'active_document_info',
        'registration_date'
    ]
    list_filter = [
        'status', 
        'property_type', 
        'land_use', 
        'district', 
        'registration_date'
    ]
    search_fields = [
        'parcel_id', 
        'owner__first_name', 
        'owner__last_name', 
        'owner__email',
        'property_address',
        'title_number'
    ]
    readonly_fields = [
        'parcel_id', 
        'created_at', 
        'updated_at',
        'coordinates_display'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('parcel_id', 'owner', 'title_number', 'status')
        }),
        ('Property Details', {
            'fields': ('property_address', 'property_type', 'land_use', 'size_hectares')
        }),
        ('Location Information', {
            'fields': ('location', 'district', 'sector', 'cell', 'village')
        }),
        ('GIS Information', {
            'fields': ('latitude', 'longitude', 'coordinates_display', 'location_point'),
            'classes': ('collapse',)
        }),
        ('Survey Information', {
            'fields': ('survey_date', 'surveyor', 'survey_accuracy'),
            'classes': ('collapse',)
        }),
        ('Registration Information', {
            'fields': ('registration_date', 'registered_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def owner_name(self, obj):
        return obj.owner.get_full_name()
    owner_name.short_description = 'Owner'
    
    def property_address_short(self, obj):
        return obj.property_address[:50] + '...' if len(obj.property_address) > 50 else obj.property_address
    property_address_short.short_description = 'Address'
    
    def active_document_info(self, obj):
        active_doc = obj.active_document
        if active_doc:
            color = 'green' if active_doc.document_type == 'certificate' else 'blue'
            expiry_info = ''
            if active_doc.document_type == 'contract' and active_doc.expiration_date:
                days_left = active_doc.days_until_expiration
                if days_left and days_left <= 90:
                    color = 'red'
                    expiry_info = f' (Expires in {days_left} days)'
            
            return format_html(
                '<span style="color: {};">{}{}</span>',
                color,
                active_doc.get_document_type_display(),
                expiry_info
            )
        return format_html('<span style="color: gray;">No active document</span>')
    active_document_info.short_description = 'Active Document'
    
    def coordinates_display(self, obj):
        if obj.coordinates:
            return f"Lat: {obj.coordinates['lat']}, Lng: {obj.coordinates['lng']}"
        return "No coordinates"
    coordinates_display.short_description = 'Coordinates'


@admin.register(ParcelApplication)
class ParcelApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'application_number',
        'applicant_name',
        'application_type',
        'property_type',
        'status',
        'submitted_at',
        'review_status'
    ]
    list_filter = [
        'application_type',
        'status',
        'property_type',
        'submitted_at',
        'review_date'
    ]
    search_fields = [
        'application_number',
        'applicant__first_name',
        'applicant__last_name',
        'applicant__email',
        'owner_first_name',
        'owner_last_name',
        'property_address'
    ]
    readonly_fields = [
        'application_number',
        'submitted_at',
        'updated_at',
        'full_owner_name'
    ]
    
    fieldsets = (
        ('Application Information', {
            'fields': ('application_number', 'applicant', 'application_type', 'status')
        }),
        ('Owner Information', {
            'fields': ('owner_first_name', 'owner_last_name', 'full_owner_name')
        }),
        ('Property Information', {
            'fields': ('property_address', 'property_type')
        }),
        ('Documents', {
            'fields': ('owner_id_document', 'sale_deed_document', 'previous_contract_document')
        }),
        ('Processing', {
            'fields': ('reviewed_by', 'field_agent', 'review_notes', 'review_date', 'approval_date', 'rejection_reason')
        }),
        ('Related Objects', {
            'fields': ('parcel',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_under_review', 'assign_field_agent']
    
    def applicant_name(self, obj):
        return obj.applicant.get_full_name()
    applicant_name.short_description = 'Applicant'
    
    def review_status(self, obj):
        if obj.status == 'submitted':
            return format_html('<span style="color: orange;">Pending Review</span>')
        elif obj.status == 'under_review':
            reviewer = obj.reviewed_by.get_full_name() if obj.reviewed_by else 'Unassigned'
            return format_html('<span style="color: blue;">Under Review by {}</span>', reviewer)
        elif obj.status == 'approved':
            return format_html('<span style="color: green;">Approved</span>')
        elif obj.status == 'rejected':
            return format_html('<span style="color: red;">Rejected</span>')
        return obj.get_status_display()
    review_status.short_description = 'Review Status'
    
    def mark_under_review(self, request, queryset):
        updated = queryset.filter(status='submitted').update(
            status='under_review',
            reviewed_by=request.user,
            review_date=timezone.now()
        )
        self.message_user(request, f'{updated} applications marked as under review.')
    mark_under_review.short_description = "Mark selected applications as under review"
    
    def assign_field_agent(self, request, queryset):
        # This would need to be implemented with a custom admin action
        # that shows a form to select field agents
        pass
    assign_field_agent.short_description = "Assign field agent to selected applications"


@admin.register(ParcelDocument)
class ParcelDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'document_number',
        'parcel_id_display',
        'document_type',
        'status',
        'issued_date',
        'expiration_info',
        'issued_by_name'
    ]
    list_filter = [
        'document_type',
        'status',
        'issued_date'
    ]
    search_fields = [
        'document_number',
        'parcel__parcel_id',
        'parcel__owner__first_name',
        'parcel__owner__last_name',
        'application__application_number'
    ]
    readonly_fields = [
        'document_number',
        'document_hash',
        'created_at',
        'updated_at',
        'is_expired',
        'is_active',
        'days_until_expiration'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('document_number', 'document_type', 'status')
        }),
        ('Related Objects', {
            'fields': ('parcel', 'application')
        }),
        ('Validity', {
            'fields': ('issued_date', 'expiration_date', 'is_expired', 'is_active', 'days_until_expiration')
        }),
        ('Digital Document', {
            'fields': ('document_file', 'document_hash')
        }),
        ('Authority', {
            'fields': ('issued_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parcel_id_display(self, obj):
        return obj.parcel.parcel_id
    parcel_id_display.short_description = 'Parcel ID'
    
    def expiration_info(self, obj):
        if obj.expiration_date:
            if obj.is_expired:
                return format_html('<span style="color: red;">Expired</span>')
            elif obj.days_until_expiration and obj.days_until_expiration <= 90:
                return format_html(
                    '<span style="color: orange;">Expires in {} days</span>',
                    obj.days_until_expiration
                )
            else:
                return obj.expiration_date.strftime('%Y-%m-%d')
        return 'No expiration'
    expiration_info.short_description = 'Expiration'
    
    def issued_by_name(self, obj):
        return obj.issued_by.get_full_name() if obj.issued_by else 'System'
    issued_by_name.short_description = 'Issued By'


@admin.register(OwnershipTransfer)
class OwnershipTransferAdmin(admin.ModelAdmin):
    list_display = [
        'transfer_number',
        'parcel_id_display',
        'current_owner_name',
        'new_owner_name',
        'transfer_type',
        'status',
        'initiated_at'
    ]
    list_filter = [
        'transfer_type',
        'status',
        'initiated_at'
    ]
    search_fields = [
        'transfer_number',
        'parcel__parcel_id',
        'current_owner__first_name',
        'current_owner__last_name',
        'new_owner__first_name',
        'new_owner__last_name'
    ]
    readonly_fields = [
        'transfer_number',
        'initiated_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Transfer Information', {
            'fields': ('transfer_number', 'parcel', 'transfer_type', 'status')
        }),
        ('Parties', {
            'fields': ('current_owner', 'new_owner', 'initiated_by')
        }),
        ('Transfer Details', {
            'fields': ('transfer_value', 'conditions', 'notes')
        }),
        ('Legal Requirements', {
            'fields': ('legal_document_required', 'notary_required', 'court_approval_required')
        }),
        ('Processing', {
            'fields': ('approved_by', 'approval_date', 'completion_date', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('initiated_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parcel_id_display(self, obj):
        return obj.parcel.parcel_id
    parcel_id_display.short_description = 'Parcel ID'
    
    def current_owner_name(self, obj):
        return obj.current_owner.get_full_name()
    current_owner_name.short_description = 'Current Owner'
    
    def new_owner_name(self, obj):
        return obj.new_owner.get_full_name()
    new_owner_name.short_description = 'New Owner'
