from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from applications.models import ParcelApplication, ParcelTitle
from disputes.models import Dispute as DisputeModel
from .mixins import SurveyorRequiredMixin

User = get_user_model()

class HomeView(TemplateView):
    template_name = 'home.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if request.user.is_authenticated and request.user.role == 'surveyor':
            return redirect('core:surveyor_dashboard')
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['user'] = user
        context['unread_notifications_count'] = user.notifications.filter(is_read=False).count()

        # ADD Dispute Officer-specific context
        if user.role == 'dispute_officer':
            # Get dispute statistics
            all_disputes = DisputeModel.objects.all()
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            context.update({
                # Overall statistics
                'total_disputes': all_disputes.count(),
                'unassigned_disputes': all_disputes.filter(
                    assigned_officer__isnull=True,
                    status='submitted'
                ).count(),
                'active_disputes': all_disputes.filter(
                    status__in=['under_investigation', 'mediation']
                ).count(),
                'resolved_this_month': all_disputes.filter(
                    status='resolved',
                    resolution_date__gte=month_start
                ).count(),
                
                # Priority breakdown
                'urgent_disputes': all_disputes.filter(
                    priority='urgent',
                    status__in=['submitted', 'under_investigation']
                ).count(),
                'high_priority_disputes': all_disputes.filter(
                    priority='high',
                    status__in=['submitted', 'under_investigation']
                ).count(),
                
                # Recent unassigned disputes
                'recent_unassigned': all_disputes.filter(
                    assigned_officer__isnull=True,
                    status='submitted'
                ).select_related('complainant', 'parcel').order_by('-filed_at')[:5],
                
                # Disputes by type
                'disputes_by_type': all_disputes.values('dispute_type').annotate(
                    count=Count('id')
                ).order_by('-count'),
                
                # Officer workload
                'officer_workload': User.objects.filter(
                    role__in=['notary', 'surveyor', 'registry_officer']
                ).annotate(
                    active_cases=Count('assigned_disputes', 
                        filter=Q(assigned_disputes__status__in=['under_investigation', 'mediation']))
                ).order_by('-active_cases')[:5],
                
                # Approach effectiveness (if data exists)
                'approach_effectiveness': DisputeModel.objects.filter(
                    suggested_approach__isnull=False,
                    status='resolved'
                ).values('suggested_approach').annotate(
                    count=Count('id')
                ).order_by('-count')[:5],
                
                # Overdue investigations (disputes older than 30 days without resolution)
                'overdue_disputes': all_disputes.filter(
                    status__in=['under_investigation', 'mediation'],
                    filed_at__lt=timezone.now() - timedelta(days=30)
                ).select_related('assigned_officer', 'parcel').order_by('filed_at')[:5],
            })
            
        # Existing Notary-specific context
        elif user.role == 'notary':
            from disputes.models import DisputeTimeline

            assigned_disputes = DisputeModel.objects.filter(
                assigned_officer=user
            ).select_related('parcel', 'complainant').order_by('-filed_at')

            context.update({
                'assigned_disputes': assigned_disputes[:5],
                'assigned_disputes_count': assigned_disputes.count(),
                'active_investigations': assigned_disputes.filter(
                    status__in=['under_investigation', 'mediation']
                ).count(),
                'resolved_this_month': assigned_disputes.filter(
                    status='resolved',
                    resolution_date__gte=timezone.now().replace(day=1)
                ).count(),
                'recent_activities': DisputeTimeline.objects.filter(
                    dispute__in=assigned_disputes
                ).select_related('dispute', 'created_by').order_by('-created_at')[:10],
                
                # Show approach guidance if exists
                'disputes_with_guidance': assigned_disputes.filter(
                    suggested_approach__isnull=False,
                    status__in=['under_investigation', 'mediation']
                ).select_related('approach_suggested_by')[:3],
            })

        # Registry Officer context - ENHANCED WITH MISSING METRICS
        elif user.role == 'registry_officer':
            # Get all users for admin-level statistics
            all_users = User.objects.all()
            
            context.update({
                # Application metrics
                'pending_applications': ParcelApplication.objects.filter(
                    status='pending'
                ).count(),
                'completed_today': ParcelApplication.objects.filter(
                    status='approved',
                    updated_at__date=timezone.now().date()
                ).count(),
                'active_titles': ParcelTitle.objects.filter(is_active=True).count(),
                
                # USER STATISTICS THAT WERE MISSING
                'total_users': all_users.count(),
                'verified_users': all_users.filter(is_verified=True).count(),
                'unverified_users': all_users.filter(is_verified=False).count(),
                'total_landowners': all_users.filter(role='landowner').count(),
                'total_officers': all_users.filter(
                    role__in=['registry_officer', 'surveyor', 'notary', 'admin']
                ).count(),
                'active_users': all_users.filter(is_active=True).count(),
                'inactive_users': all_users.filter(is_active=False).count(),
                'new_users_today': all_users.filter(
                    date_joined__date=timezone.now().date()
                ).count(),
            })

        # Admin context - ENHANCED WITH MISSING METRICS  
        elif user.role == 'admin':
            # Get all users for comprehensive statistics
            all_users = User.objects.all()
            
            context.update({
                # USER STATISTICS THAT WERE MISSING
                'total_users': all_users.count(),
                'verified_users': all_users.filter(is_verified=True).count(),
                'unverified_users': all_users.filter(is_verified=False).count(),
                'total_landowners': all_users.filter(role='landowner').count(),
                'total_officers': all_users.filter(
                    role__in=['registry_officer', 'surveyor', 'notary', 'admin']
                ).count(),
                'active_users': all_users.filter(is_active=True).count(),
                'inactive_users': all_users.filter(is_active=False).count(),
                'new_users_today': all_users.filter(
                    date_joined__date=timezone.now().date()
                ).count(),
                
                # Application and system metrics
                'total_applications': ParcelApplication.objects.count(),
                'pending_applications': ParcelApplication.objects.filter(status='pending').count(),
                'approved_applications': ParcelApplication.objects.filter(status='approved').count(),
                'field_inspection_applications': ParcelApplication.objects.filter(status='field_inspection').count(),
                
                # Dispute metrics
                'total_disputes': DisputeModel.objects.count(),
                'active_disputes': DisputeModel.objects.filter(
                    status__in=['under_investigation', 'mediation']
                ).count(),
                
                # Recent activity for admin overview
                'recent_applications': ParcelApplication.objects.order_by('-submitted_at')[:5],
                'recent_users': all_users.order_by('-date_joined')[:5],
            })

        # Landowner context - FIXED VARIABLE NAME ISSUE
        elif user.role == 'landowner':
            from land_management.models import LandParcel
            
            # Get landowner's data
            my_applications = ParcelApplication.objects.filter(applicant=user)
            my_disputes = DisputeModel.objects.filter(
                Q(complainant=user) | Q(respondent=user)
            )
            
            context.update({
                'my_parcels': LandParcel.objects.filter(owner=user).count(),
                'my_applications': my_applications.count(),
                'applications': my_applications.count(),  # Alternative variable name for template compatibility
                'my_disputes': my_disputes.count(),
                
                # Additional landowner metrics
                'pending_applications': my_applications.filter(status='submitted').count(),
                'approved_applications': my_applications.filter(status='approved').count(),
                'recent_applications': my_applications.order_by('-submitted_at')[:5],
            })

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