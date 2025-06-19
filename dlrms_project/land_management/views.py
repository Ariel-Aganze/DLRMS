from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse

# Import only the models that exist in this app
from .models import LandParcel, OwnershipTransfer, ParcelBoundary

# Import models from other apps
from applications.models import ParcelApplication, ParcelTitle
from core.mixins import RoleRequiredMixin
from notifications.models import Notification


class ParcelListView(LoginRequiredMixin, ListView):
    """View for listing land parcels"""
    model = LandParcel
    template_name = 'land_management/parcel_list.html'
    context_object_name = 'parcels'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'landowner':
            queryset = queryset.filter(owner=user)
        elif user.role == 'surveyor':
            # Show parcels from applications they've inspected
            from applications.models import ParcelApplication
            inspected_apps = ParcelApplication.objects.filter(
                field_agent=user,
                parcel__isnull=False
            ).values_list('parcel_id', flat=True)
            queryset = queryset.filter(id__in=inspected_apps)
        # Admin and registry officers see all parcels
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(parcel_id__icontains=search) |
                Q(title_number__icontains=search) |
                Q(location__icontains=search) |
                Q(owner__first_name__icontains=search) |
                Q(owner__last_name__icontains=search)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('owner').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['status_choices'] = LandParcel.PARCEL_STATUS_CHOICES
        return context


class ParcelCreateView(RoleRequiredMixin, LoginRequiredMixin, CreateView):
    """View for creating new parcels (admin/registry officer only)"""
    allowed_roles = ['admin', 'registry_officer']
    model = LandParcel
    template_name = 'land_management/parcel_create.html'
    fields = ['owner', 'location', 'district', 'sector', 'cell', 'village', 
              'size_hectares', 'property_type', 'latitude', 'longitude']
    success_url = reverse_lazy('land_management:parcel_list')
    
    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        form.instance.registration_date = timezone.now()
        form.instance.status = 'registered'
        
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Land parcel {form.instance.parcel_id} has been registered successfully!'
        )
        
        # Create notification for the owner
        if form.instance.owner != self.request.user:
            Notification.objects.create(
                recipient=form.instance.owner,
                title='New Land Parcel Registered',
                message=f'A new land parcel has been registered in your name. Parcel ID: {form.instance.parcel_id}',
                notification_type='system_alert'
            )
        
        return response


class ParcelDetailView(LoginRequiredMixin, DetailView):
    """View for displaying parcel details"""
    model = LandParcel
    template_name = 'land_management/parcel_detail.html'
    context_object_name = 'parcel'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Landowners can only see their own parcels
        if user.role == 'landowner':
            queryset = queryset.filter(owner=user)
        elif user.role == 'surveyor':
            # Surveyors can see parcels they've worked on
            from applications.models import ParcelApplication
            inspected_apps = ParcelApplication.objects.filter(
                field_agent=user,
                parcel__isnull=False
            ).values_list('parcel_id', flat=True)
            queryset = queryset.filter(id__in=inspected_apps)
        # Admin and registry officers can see all parcels
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parcel = self.object
        
        # Get active title
        context['active_title'] = parcel.get_active_title()
        
        # Get ownership transfers
        context['ownership_transfers'] = OwnershipTransfer.objects.filter(
            parcel=parcel
        ).select_related('current_owner', 'new_owner').order_by('-initiated_at')
        
        # Get related applications
        context['related_applications'] = ParcelApplication.objects.filter(
            parcel=parcel
        ).select_related('applicant', 'field_agent').order_by('-submitted_at')
        
        # Check if user can edit
        user = self.request.user
        context['can_edit'] = user.role in ['admin', 'registry_officer'] or parcel.owner == user
        
        return context


class ParcelUpdateView(RoleRequiredMixin, LoginRequiredMixin, UpdateView):
    """View for updating parcel information"""
    allowed_roles = ['admin', 'registry_officer']
    model = LandParcel
    template_name = 'land_management/parcel_update.html'
    fields = ['location', 'district', 'sector', 'cell', 'village', 
              'size_hectares', 'property_type', 'latitude', 'longitude', 'status']
    
    def get_success_url(self):
        return reverse_lazy('land_management:parcel_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            'Parcel information has been updated successfully!'
        )
        return super().form_valid(form)


class MapView(LoginRequiredMixin, TemplateView):
    """GIS Map view for visualizing parcels"""
    template_name = 'land_management/map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Base queryset with coordinates
        parcels_query = LandParcel.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).select_related('owner')
        
        # Filter based on user role
        user = self.request.user
        if user.role == 'landowner':
            parcels_query = parcels_query.filter(owner=user)
        elif user.role == 'surveyor':
            # Show parcels from applications they've inspected
            from applications.models import ParcelApplication
            inspected_apps = ParcelApplication.objects.filter(
                field_agent=user,
                parcel__isnull=False
            ).values_list('parcel_id', flat=True)
            parcels_query = parcels_query.filter(id__in=inspected_apps)
        
        # Prepare parcel data for the map
        parcel_data = []
        for parcel in parcels_query:
            parcel_info = {
                'id': parcel.id,
                'parcel_id': parcel.parcel_id,
                'owner': parcel.owner.get_full_name(),
                'location': parcel.location,
                'size': float(parcel.size_hectares),
                'property_type': parcel.get_property_type_display(),
                'status': parcel.get_status_display(),
                'lat': float(parcel.latitude),
                'lng': float(parcel.longitude),
                'has_active_title': bool(parcel.get_active_title()),
            }
            
            # Add title information if available
            active_title = parcel.get_active_title()
            if active_title:
                parcel_info['title_type'] = active_title.get_title_type_display()
                parcel_info['title_number'] = active_title.title_number
            
            parcel_data.append(parcel_info)
        
        context['parcels_json'] = parcel_data
        context['total_parcels'] = len(parcel_data)
        
        # Add map center (default to Kigali if no parcels)
        if parcel_data:
            # Calculate center from parcels
            avg_lat = sum(p['lat'] for p in parcel_data) / len(parcel_data)
            avg_lng = sum(p['lng'] for p in parcel_data) / len(parcel_data)
            context['map_center'] = {'lat': avg_lat, 'lng': avg_lng}
        else:
            # Default to Kigali
            context['map_center'] = {'lat': -1.9441, 'lng': 30.0619}
        
        return context


# Additional views for enhanced functionality
class LandOwnerDashboardView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    """Dashboard for landowners"""
    allowed_roles = ['landowner']
    template_name = 'land_management/landowner_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's parcels
        parcels = LandParcel.objects.filter(owner=user).select_related('registered_by')
        
        # Statistics
        context['total_parcels'] = parcels.count()
        context['total_hectares'] = sum(p.size_hectares for p in parcels)
        context['registered_parcels'] = parcels.filter(status='registered').count()
        
        # Get parcels with their active titles
        parcel_data = []
        for parcel in parcels:
            active_title = parcel.get_active_title()
            parcel_info = {
                'parcel': parcel,
                'active_title': active_title,
                'title_type': active_title.get_title_type_display() if active_title else None,
                'expiry_date': active_title.expiry_date if active_title else None,
                'is_expiring_soon': False
            }
            
            # Check if title is expiring within 30 days (for property contracts)
            if active_title and active_title.expiry_date:
                days_until_expiry = (active_title.expiry_date - timezone.now().date()).days
                if 0 < days_until_expiry <= 30:
                    parcel_info['is_expiring_soon'] = True
                    parcel_info['days_until_expiry'] = days_until_expiry
            
            parcel_data.append(parcel_info)
        
        context['parcel_data'] = parcel_data
        
        # Get recent applications
        context['recent_applications'] = ParcelApplication.objects.filter(
            applicant=user
        ).select_related('field_agent', 'reviewed_by').order_by('-submitted_at')[:5]
        
        # Get notifications
        context['notifications'] = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).order_by('-created_at')[:5]
        
        return context


# AJAX endpoint for parcel details
def get_parcel_details(request, parcel_id):
    """AJAX view to get parcel details"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Get parcel with permission check
        parcel = LandParcel.objects.get(id=parcel_id)
        
        # Check permissions
        user = request.user
        if user.role == 'landowner' and parcel.owner != user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get active title
        active_title = parcel.get_active_title()
        
        data = {
            'parcel_id': parcel.parcel_id,
            'owner': parcel.owner.get_full_name(),
            'location': parcel.location,
            'district': parcel.district,
            'sector': parcel.sector,
            'size_hectares': float(parcel.size_hectares),
            'property_type': parcel.get_property_type_display(),
            'status': parcel.get_status_display(),
            'coordinates': parcel.coordinates if parcel.latitude and parcel.longitude else None,
            'active_title': {
                'type': active_title.get_title_type_display(),
                'number': active_title.title_number,
                'issue_date': active_title.issue_date.strftime('%Y-%m-%d'),
                'expiry_date': active_title.expiry_date.strftime('%Y-%m-%d') if active_title.expiry_date else None,
                'is_active': active_title.is_active,
            } if active_title else None
        }
        
        return JsonResponse(data)
        
    except LandParcel.DoesNotExist:
        return JsonResponse({'error': 'Parcel not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)