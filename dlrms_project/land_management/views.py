# land_management/views.py (FIXED - Correct MRO order)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from .models import LandParcel, ParcelApplication, ParcelDocument
from .forms import ParcelApplicationForm
from core.mixins import LandownerRequiredMixin, OfficerRequiredMixin
from notifications.models import Notification

# Fixed MRO: Put LoginRequiredMixin first, then specific mixins, then base class
class LandOwnerDashboardView(LoginRequiredMixin, LandownerRequiredMixin, TemplateView):
    """Enhanced dashboard for landowners with fixed sidebar"""
    template_name = 'land_management/landowner_dashboard.html'  # Renamed to avoid conflict
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's parcels with active documents
        parcels = LandParcel.objects.filter(owner=user).prefetch_related(
            Prefetch(
                'parcel_documents',
                queryset=ParcelDocument.objects.filter(status='approved').order_by('-issued_date')
            )
        ).order_by('-created_at')
        
        # Get pending applications
        pending_applications = ParcelApplication.objects.filter(
            applicant=user,
            status__in=['submitted', 'under_review', 'field_inspection']
        ).order_by('-submitted_at')
        
        # Get recent notifications
        notifications = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Calculate statistics
        total_parcels = parcels.count()
        active_contracts = 0
        active_certificates = 0
        expiring_soon = 0
        
        for parcel in parcels:
            active_doc = parcel.active_document
            if active_doc:
                if active_doc.document_type == 'contract':
                    active_contracts += 1
                    # Check if expiring within 90 days
                    if active_doc.days_until_expiration and active_doc.days_until_expiration <= 90:
                        expiring_soon += 1
                elif active_doc.document_type == 'certificate':
                    active_certificates += 1
        
        context.update({
            'parcels': parcels,
            'pending_applications': pending_applications,
            'notifications': notifications,
            'stats': {
                'total_parcels': total_parcels,
                'active_contracts': active_contracts,
                'active_certificates': active_certificates,
                'pending_applications': pending_applications.count(),
                'expiring_soon': expiring_soon,
            }
        })
        
        return context


class ParcelApplicationCreateView(LoginRequiredMixin, LandownerRequiredMixin, CreateView):
    """View for creating new parcel applications"""
    model = ParcelApplication
    form_class = ParcelApplicationForm
    template_name = 'land_management/application_create.html'
    success_url = reverse_lazy('land_management:dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.applicant = self.request.user
        response = super().form_valid(form)
        
        # Create notification for registrar (find users with registry_officer role)
        from accounts.models import User
        registrars = User.objects.filter(role__in=['registry_officer', 'admin'])
        
        for registrar in registrars:
            Notification.objects.create(
                recipient=registrar,
                title='New Parcel Application Submitted',
                message=f'A new {form.instance.get_application_type_display()} application has been submitted by {self.request.user.get_full_name()}.',
                notification_type='application_status'
            )
        
        messages.success(
            self.request, 
            f'Your {form.instance.get_application_type_display()} application has been submitted successfully. '
            f'Application number: {form.instance.application_number}'
        )
        
        return response
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'There were errors in your application. Please check the form and try again.'
        )
        return super().form_invalid(form)


class ParcelApplicationDetailView(LoginRequiredMixin, DetailView):
    """View for displaying application details"""
    model = ParcelApplication
    template_name = 'land_management/application_detail.html'
    context_object_name = 'application'
    
    def get_queryset(self):
        # Landowners can only see their own applications
        if self.request.user.role == 'landowner':
            return ParcelApplication.objects.filter(applicant=self.request.user)
        # Officers can see all applications
        return ParcelApplication.objects.all()


class ParcelListView(LoginRequiredMixin, LandownerRequiredMixin, ListView):
    """View for listing user's parcels"""
    model = LandParcel
    template_name = 'land_management/parcel_list.html'
    context_object_name = 'parcels'
    paginate_by = 10
    
    def get_queryset(self):
        return LandParcel.objects.filter(
            owner=self.request.user
        ).prefetch_related('parcel_documents').order_by('-created_at')


class ParcelDetailView(LoginRequiredMixin, DetailView):
    """View for displaying parcel details"""
    model = LandParcel
    template_name = 'land_management/parcel_detail.html'
    context_object_name = 'parcel'
    
    def get_queryset(self):
        # Landowners can only see their own parcels
        if self.request.user.role == 'landowner':
            return LandParcel.objects.filter(owner=self.request.user)
        # Officers can see all parcels
        return LandParcel.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parcel = self.object
        
        # Get all documents for this parcel
        documents = ParcelDocument.objects.filter(
            parcel=parcel
        ).order_by('-issued_date')
        
        # Get applications for this parcel
        applications = ParcelApplication.objects.filter(
            parcel=parcel
        ).order_by('-submitted_at')
        
        context.update({
            'documents': documents,
            'applications': applications,
            'active_document': parcel.active_document,
        })
        
        return context


# Officer/Admin Views
class RegistrarDashboardView(LoginRequiredMixin, OfficerRequiredMixin, TemplateView):
    """Dashboard for registrars and officers"""
    template_name = 'land_management/registrar_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get pending applications
        pending_applications = ParcelApplication.objects.filter(
            status='submitted'
        ).order_by('-submitted_at')
        
        # Get applications under review
        under_review = ParcelApplication.objects.filter(
            status='under_review',
            reviewed_by=self.request.user
        ).order_by('-submitted_at')
        
        # Get applications for field inspection
        field_inspection = ParcelApplication.objects.filter(
            status='field_inspection'
        ).order_by('-submitted_at')
        
        # Statistics
        stats = {
            'pending_count': pending_applications.count(),
            'under_review_count': under_review.count(),
            'field_inspection_count': field_inspection.count(),
            'total_applications_today': ParcelApplication.objects.filter(
                submitted_at__date=timezone.now().date()
            ).count(),
        }
        
        context.update({
            'pending_applications': pending_applications[:10],
            'under_review': under_review[:10],
            'field_inspection': field_inspection[:10],
            'stats': stats,
        })
        
        return context


class ApplicationReviewView(LoginRequiredMixin, OfficerRequiredMixin, UpdateView):
    """View for officers to review applications"""
    model = ParcelApplication
    template_name = 'land_management/application_review.html'
    fields = ['status', 'review_notes', 'field_agent']
    
    def form_valid(self, form):
        application = form.instance
        application.reviewed_by = self.request.user
        application.review_date = timezone.now()
        
        # If approved, create the parcel and document
        if application.status == 'approved':
            self.create_parcel_and_document(application)
        
        response = super().form_valid(form)
        
        # Send notification to applicant
        Notification.objects.create(
            recipient=application.applicant,
            title=f'Application {application.status.title()}',
            message=f'Your {application.get_application_type_display()} application has been {application.status}.',
            notification_type='application_status'
        )
        
        messages.success(
            self.request,
            f'Application {application.application_number} has been {application.status}.'
        )
        
        return response
    
    def create_parcel_and_document(self, application):
        """Create parcel and document when application is approved"""
        # Create or get parcel
        parcel, created = LandParcel.objects.get_or_create(
            owner=application.applicant,
            property_address=application.property_address,
            defaults={
                'property_type': application.property_type,
                'location': application.property_address,  # Simplified
                'district': 'North Kivu',  # Default, should be configurable
                'sector': 'TBD',
                'cell': 'TBD',
                'village': 'TBD',
                'land_use': 'residential',  # Default mapping from property_type
                'status': 'registered',
                'registration_date': timezone.now(),
                'registered_by': self.request.user,
            }
        )
        
        # Link application to parcel
        application.parcel = parcel
        application.save()
        
        # Create the document
        document = ParcelDocument.objects.create(
            parcel=parcel,
            application=application,
            document_type=application.application_type,
            status='approved',
            issued_by=self.request.user,
            issued_date=timezone.now()
        )
        
        return parcel, document


class ApplicationListView(LoginRequiredMixin, OfficerRequiredMixin, ListView):
    """View for listing all applications"""
    model = ParcelApplication
    template_name = 'land_management/application_list.html'
    context_object_name = 'applications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ParcelApplication.objects.all().select_related(
            'applicant', 'reviewed_by', 'field_agent'
        ).order_by('-submitted_at')
        
        # Filter by status if specified
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(application_number__icontains=search) |
                Q(owner_first_name__icontains=search) |
                Q(owner_last_name__icontains=search) |
                Q(property_address__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ParcelApplication.APPLICATION_STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


# AJAX Views
def get_parcel_details(request, parcel_id):
    """AJAX view to get parcel details"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Check permissions
        if request.user.role == 'landowner':
            parcel = LandParcel.objects.get(id=parcel_id, owner=request.user)
        else:
            parcel = LandParcel.objects.get(id=parcel_id)
        
        active_doc = parcel.active_document
        
        data = {
            'parcel_id': parcel.parcel_id,
            'property_address': parcel.property_address,
            'property_type': parcel.get_property_type_display(),
            'status': parcel.get_status_display(),
            'active_document': {
                'type': active_doc.get_document_type_display() if active_doc else None,
                'number': active_doc.document_number if active_doc else None,
                'issued_date': active_doc.issued_date.strftime('%Y-%m-%d') if active_doc else None,
                'expiration_date': active_doc.expiration_date.strftime('%Y-%m-%d') if active_doc and active_doc.expiration_date else None,
                'days_until_expiration': active_doc.days_until_expiration if active_doc else None,
                'is_expired': active_doc.is_expired if active_doc else False,
            } if active_doc else None
        }
        
        return JsonResponse(data)
        
    except LandParcel.DoesNotExist:
        return JsonResponse({'error': 'Parcel not found'}, status=404)


# Map View
class MapView(LoginRequiredMixin, TemplateView):
    """GIS map view for visualizing parcels"""
    template_name = 'land_management/map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get parcels with coordinates
        if self.request.user.role == 'landowner':
            parcels = LandParcel.objects.filter(
                owner=self.request.user,
                location_point__isnull=False
            )
        else:
            parcels = LandParcel.objects.filter(
                location_point__isnull=False
            )
        
        # Prepare parcel data for map
        parcel_data = []
        for parcel in parcels:
            if parcel.coordinates:
                parcel_data.append({
                    'id': parcel.id,
                    'parcel_id': parcel.parcel_id,
                    'owner': parcel.owner.get_full_name(),
                    'address': parcel.property_address,
                    'coordinates': parcel.coordinates,
                    'status': parcel.status,
                })
        
        context['parcels_json'] = parcel_data
        return context