# applications/views.py
# Make sure these imports are at the top of your applications/views.py file

from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required

from .models import ParcelApplication, ParcelDocument, ParcelTitle, User
from .forms import ParcelApplicationForm, ApplicationAssignmentForm, ApplicationReviewForm
from land_management.models import LandParcel
from core.mixins import RoleRequiredMixin
import json
from django.views.generic import View
from datetime import datetime, timedelta
# Landowner Views
class ParcelApplicationCreateView(LoginRequiredMixin, CreateView):
    """View for landowners to submit parcel applications"""
    model = ParcelApplication
    form_class = ParcelApplicationForm
    template_name = 'applications/parcel_application_form.html'
    success_url = reverse_lazy('applications:parcel_application_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your parcel application has been submitted successfully.')
        return response


class ParcelApplicationListView(LoginRequiredMixin, ListView):
    """View for listing parcel applications"""
    model = ParcelApplication
    template_name = 'applications/parcel_application_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        # For landowners - show only their applications
        # For registry officers and admin - show all applications
        user = self.request.user
        if user.role in ['registry_officer', 'admin']:
            return ParcelApplication.objects.all().order_by('-submitted_at')
        return ParcelApplication.objects.filter(applicant=user).order_by('-submitted_at')


class ParcelApplicationDetailView(LoginRequiredMixin, DetailView):
    """View for viewing parcel application details"""
    model = ParcelApplication
    template_name = 'applications/parcel_application_detail.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add documents to context
        context['documents'] = self.object.documents.all()
        
        # For registry officers, add assignment form
        if self.request.user.role in ['registry_officer', 'admin'] and self.object.status == 'submitted':
            context['assignment_form'] = ApplicationAssignmentForm()
        
        # For surveyors (field agents), add review form
        if (self.request.user.role == 'surveyor' and 
            self.object.field_agent == self.request.user and 
            self.object.status == 'field_inspection'):
            context['review_form'] = ApplicationReviewForm()
        
        return context


# Registry Officer Views - FIXED MRO by putting RoleRequiredMixin first


class AssignFieldAgentView(RoleRequiredMixin, LoginRequiredMixin, FormView):
    """View for registry officers to assign field agents to applications"""
    allowed_roles = ['registry_officer', 'admin']
    form_class = ApplicationAssignmentForm
    template_name = 'applications/assign_field_agent.html'
    
    def get_success_url(self):
        return reverse('applications:parcel_application_detail', kwargs={'pk': self.kwargs['pk']})
    
    def form_valid(self, form):
        application = get_object_or_404(ParcelApplication, pk=self.kwargs['pk'])
        
        # Assign field agent and update status
        application.field_agent = form.cleaned_data['field_agent']
        application.status = 'field_inspection'
        application.save()
        
        messages.success(self.request, f'Field agent {application.field_agent.get_full_name()} assigned successfully.')
        
        # If it's an AJAX request, return JSON response
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in self.request.headers.get('Content-Type', ''):
            return JsonResponse({
                'success': True,
                'message': f'Field agent {application.field_agent.get_full_name()} assigned successfully.'
            })
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # If it's an AJAX request, return JSON response
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in self.request.headers.get('Content-Type', ''):
            return JsonResponse({
                'success': False,
                'message': 'Invalid form data',
                'errors': form.errors.as_json()
            }, status=400)
        
        return super().form_invalid(form)
    
    def post(self, request, *args, **kwargs):
        # Handle raw JSON if present
        if 'application/json' in request.headers.get('Content-Type', ''):
            try:
                data = json.loads(request.body)
                application = get_object_or_404(ParcelApplication, pk=self.kwargs['pk'])
                agent_id = data.get('agent_id')
                notes = data.get('notes', '')
                
                if not agent_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Field agent is required'
                    }, status=400)
                
                field_agent = get_object_or_404(User, id=agent_id, role='surveyor')
                
                # Update application
                application.field_agent = field_agent
                application.status = 'field_inspection'
                if notes:
                    if application.review_notes:
                        application.review_notes += f"\n\nField Agent Assignment Note: {notes}"
                    else:
                        application.review_notes = f"Field Agent Assignment Note: {notes}"
                application.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Field agent {field_agent.get_full_name()} assigned successfully.'
                })
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data'
                }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
        
        return super().post(request, *args, **kwargs)



class ReviewApplicationView(RoleRequiredMixin, LoginRequiredMixin, View):
    """View for field agents to review and approve/reject applications"""

    allowed_roles = ['surveyor', 'admin']

    def get(self, request, *args, **kwargs):
        # If GET request is made directly, redirect to surveyor inspections
        return redirect('applications:surveyor_inspections')

    def post(self, request, *args, **kwargs):
        """Handle POST requests from the inspection form"""
        application = get_object_or_404(ParcelApplication, pk=self.kwargs['pk'])

        # Only the assigned field agent can review
        if application.field_agent != self.request.user and not self.request.user.is_superuser:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'You are not authorized to review this application.'
                }, status=403)
            messages.error(request, 'You are not authorized to review this application.')
            return redirect('applications:surveyor_inspections')

        # Extract form data
        decision = request.POST.get('decision')
        review_notes = request.POST.get('review_notes')
        try:
            latitude = float(request.POST.get('latitude'))
            longitude = float(request.POST.get('longitude'))
            size_hectares = float(request.POST.get('size_hectares'))
        except (ValueError, TypeError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid coordinates or land size values.'
                }, status=400)
            messages.error(request, 'Invalid coordinates or land size values.')
            return redirect('applications:surveyor_inspections')

        if decision not in ['approve', 'reject']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid decision. Must be either "approve" or "reject".'
                }, status=400)
            messages.error(request, 'Invalid decision. Must be either "approve" or "reject".')
            return redirect('applications:surveyor_inspections')

        try:
            with transaction.atomic():
                # Update application status
                application.status = 'approved' if decision == 'approve' else 'rejected'
                application.review_notes = review_notes
                application.review_date = timezone.now()
                application.reviewed_by = self.request.user
                application.save()

                # If approved, create land parcel and title
                if decision == 'approve':
                    parcel = LandParcel.objects.create(
                        owner=application.applicant,
                        location=application.property_address,
                        property_type=application.property_type,
                        district='North Kivu',  # Default values
                        sector='Default Sector',
                        cell='Default Cell',
                        village='Default Village',
                        size_hectares=size_hectares,
                        latitude=latitude,
                        longitude=longitude,
                        status='registered',
                        registration_date=timezone.now(),
                        registered_by=self.request.user
                    )

                    # Link parcel to application
                    application.parcel = parcel
                    application.save()

                    # Determine title type and expiry
                    title_type = application.application_type
                    expiry_date = None
                    if title_type == 'property_contract':
                        expiry_date = timezone.now().date() + timedelta(days=3 * 365)

                    # Create title
                    title = ParcelTitle.objects.create(
                        parcel=parcel,
                        owner=application.applicant,
                        title_type=title_type,
                        expiry_date=expiry_date,
                        is_active=True
                    )

                    # Update parcel with active title info
                    parcel.active_title_type = title_type
                    parcel.active_title_expiry = expiry_date
                    parcel.save()

                    message = f'Application approved and {title.get_title_type_display()} issued successfully.'
                else:
                    message = 'Application rejected successfully.'

                messages.success(request, message)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'redirect_url': reverse('applications:surveyor_inspections')
                    })

                return redirect('applications:surveyor_inspections')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error processing inspection: {str(e)}'
                }, status=500)

            messages.error(request, f'Error processing inspection: {str(e)}')
            return redirect('applications:surveyor_inspections')



# View Titles
class ParcelApplicationListView(LoginRequiredMixin, ListView):
    """View for listing parcel applications"""
    model = ParcelApplication
    template_name = 'applications/parcel_application_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        user = self.request.user
        
        # For surveyors - show only applications assigned to them
        if user.role == 'surveyor':
            return ParcelApplication.objects.filter(
                field_agent=user,
                status__in=['field_inspection', 'approved', 'rejected']
            ).order_by('-submitted_at')
        
        # For landowners - show only their applications
        elif user.role == 'landowner':
            return ParcelApplication.objects.filter(applicant=user).order_by('-submitted_at')
        
        # For registry officers and admin - show all applications
        else:
            return ParcelApplication.objects.all().order_by('-submitted_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        # Add different context based on user role
        if user.role == 'surveyor':
            context['pending_inspections'] = self.get_queryset().filter(status='field_inspection')
            context['completed_inspections'] = self.get_queryset().filter(status__in=['approved', 'rejected'])
            context['is_surveyor'] = True
        elif user.role in ['registry_officer', 'admin']:
            context['is_admin'] = True
        else:
            context['is_landowner'] = True
        
        return context


class ParcelTitleDetailView(LoginRequiredMixin, DetailView):
    """View for viewing parcel title details"""
    model = ParcelTitle
    template_name = 'applications/parcel_title_detail.html'
    context_object_name = 'title'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parcel'] = self.object.parcel
        context['today'] = timezone.now().date()
        return context


# Legacy views for compatibility (keeping the same functionality)
class ApplicationListView(LoginRequiredMixin, ListView):
    """Legacy application list view"""
    model = ParcelApplication
    template_name = 'applications/application_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['registry_officer', 'admin']:
            return ParcelApplication.objects.all().order_by('-submitted_at')
        return ParcelApplication.objects.filter(applicant=user).order_by('-submitted_at')


class ApplicationCreateView(LoginRequiredMixin, CreateView):
    """Legacy application create view"""
    model = ParcelApplication
    form_class = ParcelApplicationForm
    template_name = 'applications/application_form.html'
    success_url = reverse_lazy('applications:application_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ApplicationDetailView(LoginRequiredMixin, DetailView):
    """Legacy application detail view"""
    model = ParcelApplication
    template_name = 'applications/application_detail.html'
    context_object_name = 'application'


class ApplicationUpdateView(LoginRequiredMixin, UpdateView):
    """Legacy application update view"""
    model = ParcelApplication
    form_class = ParcelApplicationForm
    template_name = 'applications/application_form.html'
    
    def get_success_url(self):
        return reverse('applications:application_detail', kwargs={'pk': self.object.pk})


class ApplicationReviewView(RoleRequiredMixin, LoginRequiredMixin, FormView):
    """Legacy application review view"""
    allowed_roles = ['registry_officer', 'admin']
    form_class = ApplicationReviewForm
    template_name = 'applications/application_review.html'
    
    def get_success_url(self):
        return reverse('applications:application_detail', kwargs={'pk': self.kwargs['pk']})
    
# Add this to your applications/views.py file

class ParcelTitleListView(LoginRequiredMixin, ListView):
    """View for listing parcel titles"""
    model = ParcelTitle
    template_name = 'applications/parcel_title_list.html'
    context_object_name = 'titles'
    
    def get_queryset(self):
        user = self.request.user
        
        # For surveyors - show titles related to their inspections
        if user.role == 'surveyor':
            # Get parcels from applications that this surveyor has inspected
            inspected_applications = ParcelApplication.objects.filter(
                field_agent=user,
                status='approved'
            )
            
            # Get the titles for these parcels
            return ParcelTitle.objects.filter(
                parcel__in=[app.parcel for app in inspected_applications if app.parcel]
            ).order_by('-issue_date')
        
        # For landowners - show only their titles
        return ParcelTitle.objects.filter(owner=self.request.user).order_by('-issue_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now().date()  # For expiry date comparison
        return context  
    

class SurveyorInspectionsView(RoleRequiredMixin, LoginRequiredMixin, ListView):
    """View for surveyors to see their assigned inspections"""
    allowed_roles = ['surveyor', 'admin']
    model = ParcelApplication
    template_name = 'applications/surveyor_inspections.html'
    context_object_name = 'inspections'
    
    def get_queryset(self):
        # Get applications assigned to this surveyor for field inspection
        return ParcelApplication.objects.filter(
            field_agent=self.request.user,
            status='field_inspection'
        ).order_by('-submitted_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add completed inspections
        context['completed_inspections'] = ParcelApplication.objects.filter(
            field_agent=self.request.user,
            status__in=['approved', 'rejected']
        ).order_by('-review_date')[:10]  # Show last 10 completed
        
        return context
    
# Add these functions to your applications/views.py file

@login_required
def get_inspection_details(request, application_id):
    """API endpoint to get inspection details for modal"""
    if request.user.role not in ['surveyor', 'admin']:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to access this resource.'
        }, status=403)
    
    try:
        application = get_object_or_404(ParcelApplication, pk=application_id)
        
        # Check if this application is assigned to the current surveyor
        if application.field_agent != request.user and request.user.role != 'admin':
            return JsonResponse({
                'success': False,
                'message': 'This application is not assigned to you.'
            }, status=403)
        
        # Return application data for the modal
        return JsonResponse({
            'success': True,
            'application': {
                'id': application.id,
                'application_number': application.application_number,
                'owner_first_name': application.owner_first_name,
                'owner_last_name': application.owner_last_name,
                'applicant_email': application.applicant.email,
                'property_address': application.property_address,
                'property_type': application.property_type,
                'application_type': application.application_type,
                'application_type_display': application.get_application_type_display(),
                'status': application.status,
                'status_display': application.get_status_display(),
                'submitted_at': application.submitted_at.strftime('%b %d, %Y')
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def get_completed_inspection_details(request, application_id):
    """API endpoint to get completed inspection details for modal"""
    if request.user.role not in ['surveyor', 'admin']:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to access this resource.'
        }, status=403)
    
    try:
        application = get_object_or_404(ParcelApplication, pk=application_id)
        
        # Check if this application was inspected by the current surveyor
        if application.field_agent != request.user and request.user.role != 'admin':
            return JsonResponse({
                'success': False,
                'message': 'This application was not inspected by you.'
            }, status=403)
        
        # Get the latitude, longitude, and size from either the parcel or directly from the inspection notes
        # This is the key fix - handling cases where the parcel might not exist
        latitude = None
        longitude = None
        size_hectares = None
        
        # If a parcel was created during approval
        if hasattr(application, 'parcel') and application.parcel:
            latitude = application.parcel.latitude
            longitude = application.parcel.longitude
            size_hectares = application.parcel.size_hectares
        else:
            # Try to extract coordinates from review notes or use defaults
            # This is a fallback when the parcel wasn't created or linked properly
            latitude = 0
            longitude = 0
            size_hectares = 0
            
            # You could implement more sophisticated parsing of the review_notes
            # to extract coordinates if they were saved there
        
        # Return application data for the modal
        return JsonResponse({
            'success': True,
            'application': {
                'id': application.id,
                'application_number': application.application_number,
                'owner_first_name': application.owner_first_name,
                'owner_last_name': application.owner_last_name,
                'property_address': application.property_address,
                'property_type': application.property_type,
                'application_type': application.application_type,
                'application_type_display': application.get_application_type_display(),
                'status': application.status,
                'status_display': application.get_status_display(),
                'latitude': latitude,
                'longitude': longitude,
                'size_hectares': size_hectares,
                'review_date': application.review_date.strftime('%b %d, %Y') if application.review_date else None,
                'review_notes': application.review_notes or "No notes provided"
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Error retrieving inspection details: {str(e)}"
        }, status=500)