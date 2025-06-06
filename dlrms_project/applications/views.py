# applications/views.py
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.db import transaction

from .models import ParcelApplication, ParcelDocument, ParcelTitle, User
from .forms import ParcelApplicationForm, ApplicationAssignmentForm, ApplicationReviewForm
from land_management.models import LandParcel
from core.mixins import RoleRequiredMixin
from django.http import JsonResponse
import json

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


# Field Agent (Surveyor) Views - FIXED MRO by putting RoleRequiredMixin first
class ReviewApplicationView(RoleRequiredMixin, LoginRequiredMixin, FormView):
    """View for field agents to review and approve/reject applications"""
    allowed_roles = ['surveyor', 'admin']
    form_class = ApplicationReviewForm
    template_name = 'applications/review_application.html'
    
    def get_success_url(self):
        return reverse('applications:parcel_application_detail', kwargs={'pk': self.kwargs['pk']})
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        return form
    
    def form_valid(self, form):
        application = get_object_or_404(ParcelApplication, pk=self.kwargs['pk'])
        
        # Only the assigned field agent can review
        if application.field_agent != self.request.user and not self.request.user.is_superuser:
            messages.error(self.request, 'You are not authorized to review this application.')
            return redirect(self.get_success_url())
        
        decision = form.cleaned_data['decision']
        review_notes = form.cleaned_data['review_notes']
        
        with transaction.atomic():
            # Update application status
            application.status = 'approved' if decision == 'approve' else 'rejected'
            application.review_notes = review_notes
            application.review_date = timezone.now()
            application.reviewed_by = self.request.user
            application.save()
            
            # If approved, create land parcel and title
            if decision == 'approve':
                # Create land parcel
                parcel = LandParcel.objects.create(
                    owner=application.applicant,
                    location=application.property_address,
                    property_type=application.property_type,
                    district='North Kivu',  # Default values
                    sector='Default Sector',
                    cell='Default Cell',
                    village='Default Village',
                    size_hectares=form.cleaned_data['size_hectares'],
                    latitude=form.cleaned_data['latitude'],
                    longitude=form.cleaned_data['longitude'],
                    status='registered',
                    registration_date=timezone.now(),
                    registered_by=self.request.user
                )
                
                # Create title based on application type
                title_type = application.application_type
                
                # Calculate expiry date for property contract (3 years)
                expiry_date = None
                if title_type == 'property_contract':
                    expiry_date = timezone.now().date() + datetime.timedelta(days=3*365)
                
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
                
                messages.success(self.request, f'Application approved and {title.get_title_type_display()} issued successfully.')
            else:
                messages.info(self.request, 'Application has been rejected.')
        
        return super().form_valid(form)


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