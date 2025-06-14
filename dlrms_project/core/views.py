# core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from applications.models import ParcelApplication, ParcelTitle

User = get_user_model()

class HomeView(TemplateView):
    template_name = 'home.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add user data to context
        context['user'] = user
        
        # Add count of unread notifications
        context['unread_notifications_count'] = user.notifications.filter(is_read=False).count()
        
        # Different context data based on user role
        if user.role == 'surveyor':
            # For surveyors, show assigned applications for field inspection
            context['assigned_applications'] = ParcelApplication.objects.filter(
                field_agent=user,
                status='field_inspection'
            ).order_by('-submitted_at')
            
            # Count of pending field inspections
            context['pending_inspections_count'] = context['assigned_applications'].count()
            
            # Completed inspections (applications that were assigned to this surveyor and are now approved/rejected)
            context['completed_inspections'] = ParcelApplication.objects.filter(
                field_agent=user,
                status__in=['approved', 'rejected']
            ).order_by('-review_date')[:5]
            
            context['completed_inspections_count'] = ParcelApplication.objects.filter(
                field_agent=user,
                status__in=['approved', 'rejected']
            ).count()
            
            # Applications awaiting field inspection (system-wide)
            if user.is_staff or user.role in ['admin', 'registry_officer']:
                context['pending_applications'] = ParcelApplication.objects.filter(
                    status='submitted'
                ).order_by('-submitted_at')[:5]
                
                context['pending_applications_count'] = ParcelApplication.objects.filter(
                    status='submitted'
                ).count()
            
        else:
            # For landowners and other roles
            context['recent_applications'] = ParcelApplication.objects.filter(applicant=user).order_by('-submitted_at')[:4]
            context['recent_parcels'] = user.land_parcels.all().order_by('-created_at')[:3]
            
            # Add pending applications count 
            context['pending_applications_count'] = ParcelApplication.objects.filter(
                applicant=user, 
                status__in=['submitted', 'under_review', 'field_inspection']
            ).count()
            
            # Add parcel titles count
            context['parcel_titles_count'] = ParcelTitle.objects.filter(
                owner=user,
                is_active=True
            ).count()
        
        # Add today's date for expiry checks
        context['today'] = timezone.now().date()
        
        # Admin-specific data (only for admin and registry_officer roles)
        if user.role in ['admin', 'registry_officer']:
            # User statistics
            all_users = User.objects.all()
            context['total_users'] = all_users.count()
            context['verified_users'] = all_users.filter(is_verified=True).count()
            context['unverified_users'] = all_users.filter(is_verified=False).count()
            context['total_landowners'] = all_users.filter(role='landowner').count()
            context['total_officers'] = all_users.filter(
                role__in=['registry_officer', 'surveyor', 'notary', 'admin']
            ).count()
            
            # Recent users for the table (last 20 users)
            context['recent_users'] = all_users.order_by('-date_joined')[:20]
        
        return context

class AboutView(TemplateView):
    template_name = 'about.html'

class ServicesView(TemplateView):
    template_name = 'services.html'

class ContactView(TemplateView):
    template_name = 'contact.html'