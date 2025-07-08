# core/views.py
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from applications.models import ParcelApplication, ParcelTitle
# Import dispute model directly at the module level and store a reference
from disputes.models import Dispute as DisputeModel  # Rename to avoid potential namespace conflicts
from .mixins import SurveyorRequiredMixin

User = get_user_model()

class HomeView(TemplateView):
    template_name = 'home.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # Let LoginRequiredMixin handle authentication first
        response = super().dispatch(request, *args, **kwargs)
        
        # If we get past the LoginRequiredMixin, the user is authenticated
        # and we can safely check the role
        if request.user.is_authenticated and request.user.role == 'surveyor':
            return redirect('core:surveyor_dashboard')
            
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['user'] = user
        context['unread_notifications_count'] = user.notifications.filter(is_read=False).count()

        # Notary-specific context
        if user.role == 'notary':
            from disputes.models import DisputeTimeline

            # Get disputes assigned to this notary
            assigned_disputes = DisputeModel.objects.filter(
                assigned_officer=user
            ).select_related('parcel', 'complainant').order_by('-filed_at')

            # Calculate statistics
            context.update({
                'assigned_disputes': assigned_disputes[:5],
                'assigned_disputes_count': assigned_disputes.count(),
                'active_investigations': assigned_disputes.filter(
                    status__in=['under_investigation', 'mediation']
                ).count(),
                'resolved_this_month': assigned_disputes.filter(
                    status='resolved',
                    resolution_date__month=timezone.now().month,
                    resolution_date__year=timezone.now().year
                ).count(),
                'pending_actions': assigned_disputes.filter(
                    status__in=['under_investigation', 'mediation']
                ).count(),
                'recent_activities': DisputeTimeline.objects.filter(
                    dispute__assigned_officer=user
                ).select_related('dispute').order_by('-created_at')[:5]
            })

        # Landowner or other roles
        else:
            context['recent_applications'] = ParcelApplication.objects.filter(applicant=user).order_by('-submitted_at')[:4]
            context['recent_parcels'] = user.land_parcels.all().order_by('-created_at')[:3]

            context['pending_applications_count'] = ParcelApplication.objects.filter(
                applicant=user,
                status__in=['submitted', 'under_review', 'field_inspection']
            ).count()

            context['parcel_titles_count'] = ParcelTitle.objects.filter(
                owner=user,
                is_active=True
            ).count()

        context['today'] = timezone.now().date()

        # Admin and Registry Officer stats
        if user.role in ['admin', 'registry_officer']:
            all_users = User.objects.all()
            context['total_users'] = all_users.count()
            context['verified_users'] = all_users.filter(is_verified=True).count()
            context['unverified_users'] = all_users.filter(is_verified=False).count()
            context['total_landowners'] = all_users.filter(role='landowner').count()
            context['total_officers'] = all_users.filter(
                role__in=['registry_officer', 'surveyor', 'notary', 'admin']
            ).count()
            context['recent_users'] = all_users.order_by('-date_joined')[:20]

            # Dispute statistics - use DisputeModel instead of Dispute
            context['total_disputes'] = DisputeModel.objects.count()
            context['open_disputes'] = DisputeModel.objects.filter(status='open').count()
            context['pending_disputes'] = DisputeModel.objects.filter(status='open').count()  # Mapping 'open' to 'pending'
            context['disputes_under_investigation'] = DisputeModel.objects.filter(status='under_investigation').count()
            context['disputes_in_mediation'] = DisputeModel.objects.filter(status='mediation').count()
            context['resolved_disputes'] = DisputeModel.objects.filter(status='resolved').count()
            context['recent_disputes'] = DisputeModel.objects.order_by('-filed_at')[:5]

        return context

class SurveyorDashboardView(SurveyorRequiredMixin, TemplateView):
    template_name = 'surveyor_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get documents model
        from documents.models import Document
        
        # Applications assigned for field inspection
        assigned_applications = ParcelApplication.objects.filter(
            field_agent=user,
            status='field_inspection'
        ).select_related('applicant').order_by('-submitted_at')
        
        # Disputes assigned to surveyor for investigation or mediation
        assigned_disputes = DisputeModel.objects.filter(
            assigned_officer=user,
            status__in=['under_investigation', 'mediation'],
            dispute_type__in=['boundary', 'encroachment']
        ).select_related('parcel', 'complainant').order_by('-filed_at')
        
        # Recent field activities
        recent_field_activities = ParcelApplication.objects.filter(
            field_agent=user
        ).order_by('-updated_at')[:10]
        
        # Get application IDs instead of property_id which doesn't exist
        # If you need property IDs, you might need to access a related model
        assigned_application_ids = assigned_applications.values_list('id', flat=True)
        
        # Performance metrics
        completed_inspections = ParcelApplication.objects.filter(
            field_agent=user,
            status__in=['approved', 'rejected']
        )
        
        # Check if deadline field exists
        deadline_field_exists = 'deadline' in [f.name for f in ParcelApplication._meta.get_fields()]
        
        # Upcoming deadlines - only filter by deadline if the field exists
        if deadline_field_exists:
            upcoming_deadlines = assigned_applications.filter(
                deadline__gte=timezone.now().date()
            ).order_by('deadline')[:5]
            upcoming_deadlines_count = upcoming_deadlines.count()
        else:
            upcoming_deadlines = []
            upcoming_deadlines_count = 0
        
        # Check if priority field exists
        priority_field_exists = 'priority' in [f.name for f in ParcelApplication._meta.get_fields()]
        
        # Urgent inspections - only filter by priority if the field exists
        if priority_field_exists:
            urgent_inspections = assigned_applications.filter(
                priority='high'
            ).count()
        else:
            urgent_inspections = 0
        
        context.update({
            'user': user,
            'unread_notifications_count': user.notifications.filter(is_read=False).count(),
            'assigned_applications': assigned_applications[:5],
            'pending_inspections_count': assigned_applications.count(),
            'assigned_disputes': assigned_disputes[:3],
            'assigned_disputes_count': assigned_disputes.count(),
            'completed_inspections': completed_inspections.order_by('-review_date')[:5],
            'completed_inspections_count': completed_inspections.count(),
            'recent_field_activities': recent_field_activities,
            'upcoming_deadlines': upcoming_deadlines,
            'today': timezone.now().date(),
            'urgent_inspections': urgent_inspections,
            'upcoming_deadlines_count': upcoming_deadlines_count,
            'recent_reports': Document.objects.filter(
                uploaded_by=user, 
                document_type='inspection_report'
            ).order_by('-uploaded_at')[:3]
        })
        
        return context

class AboutView(TemplateView):
    template_name = 'about.html'

class ServicesView(TemplateView):
    template_name = 'services.html'

class ContactView(TemplateView):
    template_name = 'contact.html'