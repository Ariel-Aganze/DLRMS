from django.contrib import admin
from .models import Dispute, DisputeComment, DisputeEvidence, DisputeTimeline, MediationSession

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['dispute_number', 'title', 'dispute_type', 'status', 'priority', 'complainant', 'filed_at']
    list_filter = ['status', 'dispute_type', 'priority', 'filed_at']
    search_fields = ['dispute_number', 'title', 'description', 'complainant__username', 'respondent__username']
    readonly_fields = ['dispute_number', 'filed_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dispute_number', 'title', 'description', 'dispute_type', 'priority', 'status')
        }),
        ('Parties', {
            'fields': ('complainant', 'respondent', 'parcel', 'related_application')
        }),
        ('Case Management', {
            'fields': ('assigned_officer', 'investigation_notes', 'resolution', 'resolution_date')
        }),
        ('Timestamps', {
            'fields': ('filed_at', 'updated_at')
        }),
    )

@admin.register(DisputeComment)
class DisputeCommentAdmin(admin.ModelAdmin):
    list_display = ['dispute', 'author', 'comment', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['dispute__dispute_number', 'author__username', 'comment']

@admin.register(DisputeEvidence)
class DisputeEvidenceAdmin(admin.ModelAdmin):
    list_display = ['dispute', 'title', 'evidence_type', 'submitted_by', 'submitted_at']
    list_filter = ['evidence_type', 'submitted_at']
    search_fields = ['dispute__dispute_number', 'title', 'description']

@admin.register(DisputeTimeline)
class DisputeTimelineAdmin(admin.ModelAdmin):
    list_display = ['dispute', 'event', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['dispute__dispute_number', 'event', 'description']

@admin.register(MediationSession)
class MediationSessionAdmin(admin.ModelAdmin):
    list_display = ['dispute', 'scheduled_date', 'location', 'mediator', 'outcome']
    list_filter = ['scheduled_date', 'outcome']
    search_fields = ['dispute__dispute_number', 'location', 'notes']