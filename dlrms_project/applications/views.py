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
import json
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView

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
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected field agent not found or not a surveyor'
                }, status=404)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return JsonResponse({
                    'success': False,
                    'message': f'Error assigning field agent: {str(e)}'
                }, status=500)
        
        # Proceed with normal form processing
        return super().post(request, *args, **kwargs)




class ReviewApplicationView(RoleRequiredMixin, LoginRequiredMixin, View):
    """View for field agents to submit inspection reports"""
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
                    'message': 'You are not authorized to submit this inspection report.'
                }, status=403)
            messages.error(request, 'You are not authorized to submit this inspection report.')
            return redirect('applications:surveyor_inspections')
        
        # Extract form data
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
        
        try:
            with transaction.atomic():
                # Update application status to inspection_completed
                application.status = 'inspection_completed'
                application.review_notes = review_notes
                application.review_date = timezone.now()
                application.reviewed_by = self.request.user
                
                # Store coordinates and size in the application for later use
                application.latitude = latitude
                application.longitude = longitude
                application.size_hectares = size_hectares
                application.save()
                
                message = 'Inspection report submitted successfully. Waiting for registry officer approval.'
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
                    'message': f'Error submitting inspection report: {str(e)}'
                }, status=500)

            messages.error(request, f'Error submitting inspection report: {str(e)}')
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
    

class EnhancedParcelApplicationDetailView(LoginRequiredMixin, DetailView):
    """Enhanced view for viewing parcel application details with better UI"""
    model = ParcelApplication
    template_name = 'applications/parcel_application_detail_enhanced.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add documents to context
        context['documents'] = self.object.documents.all()
        
        # Add field agents for the dropdown
        if self.request.user.role in ['registry_officer', 'admin'] and self.object.status == 'submitted':
            # Get all users with 'surveyor' role
            context['field_agents'] = User.objects.filter(role='surveyor').order_by('first_name')
        
        # Try to get boundary data if available
        try:
            from land_management.models import ParcelBoundary
            
            try:
                boundary = ParcelBoundary.objects.get(application=self.object)
                context['boundary'] = boundary
                context['has_polygon'] = True
            except ParcelBoundary.DoesNotExist:
                context['has_polygon'] = False
        except ImportError:
            context['has_polygon'] = False
        
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
        
        # Get the latitude, longitude, and size from the application
        latitude = application.latitude
        longitude = application.longitude
        size_hectares = application.size_hectares
        
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
    



class FieldInspectionView(RoleRequiredMixin, LoginRequiredMixin, DetailView):
    """View for field agents to perform inspections on a separate page"""
    allowed_roles = ['surveyor', 'admin']
    model = ParcelApplication
    template_name = 'applications/field_inspection.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add application_id as a hidden field
        context['application_id'] = self.object.id
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests for submitting inspections"""
        application = self.get_object()
        print(f"Processing field inspection submission for application {application.id}")
        
        # Only the assigned field agent can review
        if application.field_agent != self.request.user and not self.request.user.is_superuser:
            messages.error(request, 'You are not authorized to review this application.')
            return redirect('applications:surveyor_inspections')
        
        try:
            # Extract form data
            review_notes = request.POST.get('review_notes', '')
            
            # Get coordinates and size from form
            try:
                latitude = float(request.POST.get('latitude', 0))
                longitude = float(request.POST.get('longitude', 0))
                size_hectares = float(request.POST.get('size_hectares', 0))
                print(f"Form data - lat: {latitude}, lng: {longitude}, size: {size_hectares}")
            except (ValueError, TypeError) as e:
                print(f"Error parsing form data: {str(e)}")
                messages.error(request, 'Invalid coordinates or land size values. Please check your measurements.')
                return self.render_to_response(self.get_context_data())
            
            # Save boundary data if not already saved via API
            from land_management.models import ParcelBoundary
            try:
                # Check if a boundary already exists
                boundary = ParcelBoundary.objects.get(application=application)
                print(f"Found existing boundary: {boundary.id}")
                
                # Update with form data if needed
                if not boundary.center_lat or not boundary.center_lng or not boundary.area_hectares:
                    boundary.center_lat = latitude
                    boundary.center_lng = longitude
                    boundary.area_hectares = size_hectares
                    boundary.updated_by = request.user
                    boundary.save()
                    print(f"Updated existing boundary with form data")
            except ParcelBoundary.DoesNotExist:
                # Create a new boundary if one doesn't exist
                print(f"No boundary found, creating one from form data")
                
                # Create a simple square boundary if no polygon was drawn
                # This is a fallback for when the polygon wasn't saved via API
                lat_offset = 0.001  # Roughly 100m
                lng_offset = 0.001
                
                polygon_data = [
                    [latitude - lat_offset, longitude - lng_offset],
                    [latitude - lat_offset, longitude + lng_offset],
                    [latitude + lat_offset, longitude + lng_offset],
                    [latitude + lat_offset, longitude - lng_offset]
                ]
                
                # Calculate approximate area
                area_sqm = 111319.9 * 111319.9 * lat_offset * 2 * lng_offset * 2
                
                # Create the boundary
                boundary = ParcelBoundary.objects.create(
                    application=application,
                    polygon_geojson=json.dumps(polygon_data),
                    center_lat=latitude,
                    center_lng=longitude,
                    area_sqm=area_sqm,
                    area_hectares=size_hectares,
                    created_by=request.user
                )
                print(f"Created new boundary {boundary.id} from form data")
            
            # Update application
            application.review_notes = review_notes
            application.latitude = latitude
            application.longitude = longitude
            application.size_hectares = size_hectares
            application.review_date = timezone.now()
            application.status = 'inspection_completed'
            application.save()
            
            print(f"Updated application status to 'inspection_completed'")
            
            # Add success message and redirect
            messages.success(request, 'Inspection report submitted successfully.')
            return redirect('applications:surveyor_inspections')
            
        except Exception as e:
            print(f"Error in field inspection submission: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'An error occurred: {str(e)}')
            return self.render_to_response(self.get_context_data())

@login_required
def get_polygon_data(request, application_id):
    """API endpoint to retrieve polygon boundary data for a parcel"""
    print(f"get_polygon_data called for application {application_id}")
    print(f"User: {request.user.username}, Role: {getattr(request.user, 'role', 'unknown')}")
    
    if request.method != 'GET':
        print(f"Method not allowed: {request.method}")
        return JsonResponse({
            'success': False,
            'message': 'Only GET requests are supported.'
        }, status=405)
    
    try:
        # Get the application
        application = get_object_or_404(ParcelApplication, pk=application_id)
        print(f"Found application: {application}")
        
        # Check if the user has permission to view this application
        if (request.user.role not in ['registry_officer', 'admin', 'surveyor'] and 
            application.applicant != request.user):
            print(f"Permission denied: User role is {request.user.role}")
            return JsonResponse({
                'success': False,
                'message': 'You do not have permission to view this application.'
            }, status=403)
        
        # Import the ParcelBoundary model
        from land_management.models import ParcelBoundary
        
        try:
            # Try to get the boundary data
            boundary = ParcelBoundary.objects.get(application=application)
            print(f"Found boundary: {boundary.id}")
            print(f"Polygon data: {boundary.polygon_geojson[:100]}...")  # Print first 100 chars
            
            # Return the polygon data - don't try to parse it, just send as is
            return JsonResponse({
                'success': True,
                'polygon': boundary.polygon_geojson,
                'center_lat': float(boundary.center_lat) if boundary.center_lat else float(application.latitude),
                'center_lng': float(boundary.center_lng) if boundary.center_lng else float(application.longitude),
                'area_sqm': float(boundary.area_sqm) if boundary.area_sqm else None,
                'area_hectares': float(boundary.area_hectares) if boundary.area_hectares else float(application.size_hectares)
            })
        except ParcelBoundary.DoesNotExist:
            print(f"No boundary found for application {application_id}")
            
            # If no boundary data exists, return the application's basic location info
            return JsonResponse({
                'success': False,
                'message': 'No boundary data available for this application.',
                'center_lat': float(application.latitude),
                'center_lng': float(application.longitude),
                'area_hectares': float(application.size_hectares)
            })
            
    except Exception as e:
        print(f"Error in get_polygon_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving boundary data: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
def save_polygon_data(request, application_id):
    """API endpoint to save polygon boundary data for a parcel"""
    print(f"save_polygon_data called for application {application_id}")
    print(f"Request method: {request.method}")
    print(f"User: {request.user.username}, Role: {getattr(request.user, 'role', 'unknown')}")
    
    if request.user.role not in ['surveyor', 'admin']:
        print(f"Permission denied: User role is {request.user.role}")
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to perform this action.'
        }, status=403)
    
    if request.method != 'POST':
        print(f"Method not allowed: {request.method}")
        return JsonResponse({
            'success': False,
            'message': 'Only POST requests are supported.'
        }, status=405)
    
    try:
        # Get the application
        application = get_object_or_404(ParcelApplication, pk=application_id)
        print(f"Found application: {application}")
        
        # Check if this application is assigned to the current surveyor
        if application.field_agent != request.user and request.user.role != 'admin':
            print(f"Unauthorized: Application field agent is {application.field_agent}, user is {request.user}")
            return JsonResponse({
                'success': False,
                'message': 'You are not authorized to modify this application.'
            }, status=403)
        
        # Parse JSON data from request
        body = request.body.decode('utf-8')
        print(f"Request body: {body[:200]}...")  # Print first 200 chars to avoid flooding logs
        data = json.loads(body)
        print(f"Parsed data keys: {data.keys()}")
        polygon_data = data.get('polygon', [])
        center_lat = data.get('center_lat')
        center_lng = data.get('center_lng')
        area_sqm = data.get('area_sqm')
        area_hectares = data.get('area_hectares')
        
        print(f"Polygon data length: {len(polygon_data)}")
        print(f"Center: {center_lat}, {center_lng}")
        print(f"Area: {area_sqm} sqm, {area_hectares} hectares")
        
        # Import the ParcelBoundary model
        from land_management.models import ParcelBoundary
        
        # Create or update ParcelBoundary
        boundary, created = ParcelBoundary.objects.get_or_create(
            application=application,
            defaults={
                'polygon_geojson': json.dumps(polygon_data),
                'center_lat': center_lat,
                'center_lng': center_lng,
                'area_sqm': area_sqm,
                'area_hectares': area_hectares,
                'created_by': request.user
            }
        )
        
        if not created:
            print(f"Updating existing boundary: {boundary.id}")
            boundary.polygon_geojson = json.dumps(polygon_data)
            boundary.center_lat = center_lat
            boundary.center_lng = center_lng
            boundary.area_sqm = area_sqm
            boundary.area_hectares = area_hectares
            boundary.updated_by = request.user
            boundary.updated_at = timezone.now()
            boundary.save()
        else:
            print(f"Created new boundary: {boundary.id}")
        
        # Update the application with the center coordinates and area
        application.latitude = center_lat
        application.longitude = center_lng
        application.size_hectares = area_hectares
        
        # Update application status to inspection_completed if it's in field_inspection status
        if application.status == 'field_inspection':
            print(f"Updating application status from {application.status} to inspection_completed")
            application.status = 'inspection_completed'
        
        application.save()
        print(f"Application updated successfully")
        
        return JsonResponse({
            'success': True,
            'message': 'Boundary data saved successfully.'
        })
    except Exception as e:
        print(f"Error in save_polygon_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error saving boundary data: {str(e)}'
        }, status=500)


class PropertyBoundaryMapView(LoginRequiredMixin, DetailView):
    """View for displaying the property boundary map in a full page"""
    model = ParcelApplication
    template_name = 'applications/property_boundary_map.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Try to get boundary data if available
        try:
            from land_management.models import ParcelBoundary
            
            try:
                boundary = ParcelBoundary.objects.get(application=self.object)
                context['boundary'] = boundary
                context['has_polygon'] = True
                # This is useful for debugging
                context['polygon_data'] = boundary.polygon_geojson
            except ParcelBoundary.DoesNotExist:
                context['has_polygon'] = False
        except ImportError:
            context['has_polygon'] = False
        
        # Add a back URL for the return link
        context['back_url'] = self.request.GET.get('back_url', reverse('applications:parcel_application_detail_enhanced', kwargs={'pk': self.object.pk}))
        
        return context