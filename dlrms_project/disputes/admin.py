from django.contrib import admin
from .models import Dispute, DisputeComment, DisputeEvidence, DisputeTimeline, MediationSession, ApproachEffectiveness

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['dispute_number', 'title', 'dispute_type', 'status', 'priority', 
                    'complainant', 'assigned_officer', 'suggested_approach', 'filed_at']
    list_filter = ['status', 'dispute_type', 'priority', 'suggested_approach', 'filed_at']
    search_fields = ['dispute_number', 'title', 'description', 'complainant__username', 
                     'respondent__username', 'assigned_officer__username']
    readonly_fields = ['dispute_number', 'filed_at', 'updated_at', 'approach_suggested_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dispute_number', 'title', 'description', 'dispute_type', 'priority', 'status')
        }),
        ('Parties', {
            'fields': ('complainant', 'respondent', 'respondent_name', 'parcel', 'related_application')
        }),
        ('Case Management', {
            'fields': ('assigned_officer', 'investigation_notes', 'resolution', 'resolution_date')
        }),
        ('Resolution Approach Guidance', {
            'fields': ('suggested_approach', 'approach_notes', 'approach_suggested_by', 'approach_suggested_at'),
            'classes': ('collapse',)
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
    list_filter = ['created_at', 'event']
    search_fields = ['dispute__dispute_number', 'event', 'description']

@admin.register(MediationSession)
class MediationSessionAdmin(admin.ModelAdmin):
    list_display = ['dispute', 'scheduled_date', 'location', 'mediator', 'outcome']
    list_filter = ['scheduled_date', 'outcome']
    search_fields = ['dispute__dispute_number', 'location', 'notes']

# ADD NEW ADMIN FOR APPROACH EFFECTIVENESS
@admin.register(ApproachEffectiveness)
class ApproachEffectivenessAdmin(admin.ModelAdmin):
    list_display = ['dispute_type', 'approach', 'success_count', 'total_count', 
                    'success_rate_display', 'average_resolution_days']
    list_filter = ['dispute_type', 'approach']
    readonly_fields = ['created_at', 'updated_at']
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Success Rate'
    
    fieldsets = (
        ('Dispute and Approach', {
            'fields': ('dispute_type', 'approach')
        }),
        ('Statistics', {
            'fields': ('success_count', 'total_count', 'average_resolution_days')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )