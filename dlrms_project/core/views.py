from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q

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
        
        # Add recent applications and parcels
        context['recent_applications'] = user.applications.all().order_by('-submitted_at')[:3]
        context['recent_parcels'] = user.land_parcels.all().order_by('-created_at')[:3]
        
        # Add pending applications count (calculated in view to avoid template filter issues)
        context['pending_applications_count'] = user.applications.filter(status='submitted').count()
        
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