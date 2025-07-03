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
# Land Tranfer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse, Http404
from django.template.loader import get_template
from xhtml2pdf import pisa
from datetime import datetime, timedelta
from .forms import TransferInitiationForm, ReceiverConfirmationForm, TransferReviewForm
from disputes.models import Dispute
from django.contrib.auth.decorators import login_required
from io import BytesIO
from django.core.files.base import ContentFile


User = get_user_model()



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

class MyLandTitlesView(LoginRequiredMixin, ListView):
    """View for landowners to see their land titles"""
    model = ParcelTitle
    template_name = 'land_management/my_land_titles.html'
    context_object_name = 'titles'
    
    def get_queryset(self):
        # Get titles where user is the current owner and title is active
        return ParcelTitle.objects.filter(
            parcel__owner=self.request.user,
            is_active=True  # Changed from status='active' to is_active=True
        ).select_related('parcel').order_by('-issue_date')


class LandTitleDetailView(LoginRequiredMixin, DetailView):
    """View for displaying land title details with transfer option"""
    model = ParcelTitle
    template_name = 'land_management/land_title_detail.html'
    context_object_name = 'title'
    
    def get_object(self):
        title = super().get_object()
        # Ensure user owns this title
        if title.parcel.owner != self.request.user and self.request.user.role not in ['admin', 'registry_officer']:
            raise Http404("You don't have permission to view this title.")
        return title
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parcel = self.object.parcel
        
        # Check for pending transfers
        context['pending_transfer'] = OwnershipTransfer.objects.filter(
            parcel=parcel,
            status__in=['initiated', 'awaiting_receiver', 'under_review']
        ).first()
        
        # Check for active disputes
        context['active_disputes'] = Dispute.objects.filter(
            parcel=parcel,
            status__in=['open', 'under_investigation', 'mediation']
        ).exists()
        
        return context


class InitiateTransferView(LoginRequiredMixin, CreateView):
    """View for initiating ownership transfer"""
    model = OwnershipTransfer
    form_class = TransferInitiationForm
    template_name = 'land_management/initiate_transfer.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.title = get_object_or_404(ParcelTitle, pk=kwargs['title_pk'])
        self.parcel = self.title.parcel
        
        # Verify ownership
        if self.parcel.owner != request.user:
            messages.error(request, "You can only transfer land that you own.")
            return redirect('land_management:my_titles')
        
        # Check for pending transfers
        pending_transfer = OwnershipTransfer.objects.filter(
            parcel=self.parcel,
            status__in=['initiated', 'awaiting_receiver', 'under_review']
        ).first()
        
        if pending_transfer:
            messages.warning(request, "There's already a pending transfer for this land.")
            return redirect('land_management:title_detail', pk=self.title.pk)
        
        # Check for active disputes
        if Dispute.objects.filter(
            parcel=self.parcel,
            status__in=['open', 'under_investigation', 'mediation']
        ).exists():
            messages.error(request, "Cannot transfer land with active disputes.")
            return redirect('land_management:title_detail', pk=self.title.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parcel'] = self.parcel
        kwargs['title'] = self.title
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parcel'] = self.parcel
        context['title'] = self.title
        return context
    
    def form_valid(self, form):
        with transaction.atomic():
            # Set transfer details
            form.instance.parcel = self.parcel
            form.instance.title = self.title
            form.instance.current_owner = self.request.user
            
            # Try to find the new owner by national ID
            try:
                new_owner = User.objects.get(national_id=form.cleaned_data['receiver_national_id'])
                form.instance.new_owner = new_owner
                form.instance.status = 'awaiting_receiver'
                
                # Save the transfer first
                response = super().form_valid(form)
                
                # Now create the notification after the transfer is saved
                Notification.objects.create(
                    recipient=new_owner,
                    title='Land Transfer Request',
                    message=f'{self.request.user.get_full_name()} wants to transfer land (Parcel: {self.parcel.parcel_id}) to you. Please confirm within 3 days.',
                    notification_type='transfer_status',
                    related_transfer=form.instance  # Now form.instance has been saved
                )
                
                messages.success(self.request, "Transfer initiated successfully. Waiting for receiver confirmation.")
                return response
                
            except User.DoesNotExist:
                messages.error(self.request, "No user found with that National ID.")
                return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('land_management:title_detail', kwargs={'pk': self.title.pk})


@login_required
def check_receiver_details(request):
    """AJAX view to check receiver details by national ID"""
    national_id = request.GET.get('national_id')
    if not national_id:
        return JsonResponse({'found': False})
    
    try:
        user = User.objects.get(national_id=national_id)
        return JsonResponse({
            'found': True,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone_number,
            'email': user.email
        })
    except User.DoesNotExist:
        return JsonResponse({'found': False})


class TransferConfirmationView(LoginRequiredMixin, UpdateView):
    """View for receiver to confirm transfer"""
    model = OwnershipTransfer
    form_class = ReceiverConfirmationForm
    template_name = 'land_management/transfer_confirmation.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Verify receiver
        if self.object.new_owner != request.user:
            messages.error(request, "You are not the designated receiver for this transfer.")
            return redirect('core:dashboard')
        
        # Check status
        if self.object.status != 'awaiting_receiver':
            messages.error(request, "This transfer is no longer awaiting your confirmation.")
            return redirect('core:dashboard')
        
        # Check deadline
        if self.object.is_expired:
            self.object.status = 'canceled'
            self.object.save()
            messages.error(request, "The confirmation deadline has passed. Transfer canceled.")
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        with transaction.atomic():
            form.instance.status = 'under_review'
            form.instance.receiver_confirmed_at = timezone.now()
            
            response = super().form_valid(form)
            
            # Notify notaries
            notaries = User.objects.filter(role='notary')
            for notary in notaries:
                Notification.objects.create(
                    recipient=notary,
                    title='New Transfer for Review',
                    message=f'Transfer {self.object.transfer_number} is ready for review.',
                    notification_type='approval_required',
                    related_transfer=self.object
                )
            
            # Notify current owner
            Notification.objects.create(
                recipient=self.object.current_owner,
                title='Transfer Confirmed by Receiver',
                message=f'{self.object.new_owner.get_full_name()} has confirmed the transfer. Awaiting notary review.',
                notification_type='transfer_status',
                related_transfer=self.object
            )
            
            messages.success(self.request, "Transfer confirmed successfully. Awaiting notary review.")
            return response
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class TransferListView(RoleRequiredMixin, LoginRequiredMixin, ListView):
    """View for notaries to see transfers pending review"""
    allowed_roles = ['notary', 'admin', 'registry_officer']
    model = OwnershipTransfer
    template_name = 'land_management/transfer_list.html'
    context_object_name = 'transfers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.GET.get('status', 'under_review')
        if status == 'all':
            return queryset.order_by('-initiated_at')
        
        return queryset.filter(status=status).order_by('-initiated_at')


class TransferReviewView(RoleRequiredMixin, LoginRequiredMixin, UpdateView):
    """View for notary to review and approve/reject transfer"""
    allowed_roles = ['notary', 'admin', 'registry_officer']
    model = OwnershipTransfer
    form_class = TransferReviewForm
    template_name = 'land_management/transfer_review.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if self.object.status != 'under_review':
            messages.error(request, "This transfer is not under review.")
            return redirect('land_management:transfer_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transfer = self.object
        
        # Get active disputes
        context['active_disputes'] = Dispute.objects.filter(
            parcel=transfer.parcel,
            status__in=['open', 'under_investigation', 'mediation']
        )
        
        # Get parcel history
        context['previous_transfers'] = OwnershipTransfer.objects.filter(
            parcel=transfer.parcel,
            status='approved'
        ).order_by('-completed_at')[:5]
        
        return context
    
    def form_valid(self, form):
        decision = form.data.get('decision')
        
        with transaction.atomic():
            form.instance.reviewed_by = self.request.user
            form.instance.review_date = timezone.now()
            form.instance.status = decision
            
            if decision == 'approved':
                form.instance.completed_at = timezone.now()
                
                # Update parcel owner
                parcel = form.instance.parcel
                parcel.owner = form.instance.new_owner
                parcel.save()
                
                # Update title status
                old_title = form.instance.title
                old_title.status = 'transferred'
                old_title.save()
                
                # Generate transfer certificate
                self._generate_transfer_certificate(form.instance)
                
                message = "Transfer approved successfully."
            else:
                message = "Transfer rejected."
            
            response = super().form_valid(form)
            
            # Notify both parties
            for user in [form.instance.current_owner, form.instance.new_owner]:
                Notification.objects.create(
                    recipient=user,
                    title=f'Transfer {decision.title()}',
                    message=f'Transfer {form.instance.transfer_number} has been {decision}. Review notes: {form.instance.review_notes}',
                    notification_type='transfer_status',
                    related_transfer=form.instance
                )
            
            messages.success(self.request, message)
            return response
    
    def _generate_transfer_certificate(self, transfer):
        """Generate PDF transfer certificate"""
        try:
            # Import the certificate generator
            from certificates.certificate_generator import TransferCertificateGenerator
            
            # Create generator instance
            generator = TransferCertificateGenerator()
            
            # Generate the PDF
            pdf_content = generator.generate_transfer_certificate(
                transfer=transfer,
                notary=self.request.user
            )
            
            # Save PDF to transfer model
            transfer.transfer_certificate.save(
                f'transfer_certificate_{transfer.transfer_number}.pdf',
                ContentFile(pdf_content)
            )
            
            return True
        except Exception as e:
            print(f"Error generating transfer certificate: {e}")
            return False
    def get_success_url(self):
        return reverse_lazy('land_management:transfer_list')


@login_required
def cancel_transfer(request, pk):
    """View to cancel a transfer"""
    transfer = get_object_or_404(OwnershipTransfer, pk=pk)
    
    # Only current owner can cancel
    if transfer.current_owner != request.user:
        messages.error(request, "You don't have permission to cancel this transfer.")
        return redirect('core:dashboard')
    
    # Can only cancel if not yet reviewed
    if transfer.status not in ['initiated', 'awaiting_receiver']:
        messages.error(request, "Cannot cancel transfer at this stage.")
        return redirect('land_management:title_detail', pk=transfer.title.pk)
    
    transfer.status = 'canceled'
    transfer.save()
    
    # Notify receiver if applicable
    if transfer.status == 'awaiting_receiver':
        Notification.objects.create(
            recipient=transfer.new_owner,
            title='Transfer Canceled',
            message=f'{transfer.current_owner.get_full_name()} has canceled the land transfer.',
            notification_type='transfer_status',
            related_transfer=transfer
        )
    
    messages.success(request, "Transfer canceled successfully.")
    return redirect('land_management:title_detail', pk=transfer.title.pk)


@login_required
def download_transfer_certificate(request, pk):
    """Download transfer certificate PDF"""
    transfer = get_object_or_404(OwnershipTransfer, pk=pk)
    
    # Check permissions
    allowed_users = [transfer.current_owner, transfer.new_owner]
    allowed_roles = ['admin', 'registry_officer', 'notary']
    
    if request.user not in allowed_users and request.user.role not in allowed_roles:
        raise Http404("You don't have permission to download this certificate.")
    
    if not transfer.transfer_certificate:
        raise Http404("Transfer certificate not found.")
    
    response = HttpResponse(transfer.transfer_certificate.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="transfer_certificate_{transfer.transfer_number}.pdf"'
    return response