from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
import json
import csv
from datetime import datetime, timedelta

from notifications.models import Notification

from .models import ParcelApplication, ParcelDocument, ParcelTitle
from .forms import ParcelApplicationForm, ApplicationAssignmentForm, ApplicationReviewForm
from land_management.models import LandParcel
from accounts.models import User
from core.mixins import RoleRequiredMixin


class ApplicationsReviewDashboardView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    """Enhanced applications review dashboard for registry officers and admins"""
    allowed_roles = ['registry_officer', 'admin']
    template_name = 'applications/review_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all applications with related data
        applications = ParcelApplication.objects.select_related(
            'applicant', 'field_agent', 'reviewed_by'
        ).prefetch_related('documents')
        
        # Calculate statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        stats = {
            'pending_review': applications.filter(status='submitted').count(),
            'under_inspection': applications.filter(status='field_inspection').count(),
            'approved_today': applications.filter(
                status='approved', 
                review_date__date=today
            ).count(),
            'overdue_reviews': applications.filter(
                status__in=['submitted', 'under_review'],
                submitted_at__date__lt=today - timedelta(days=5)
            ).count(),
            'total_applications': applications.count(),
            'approved_this_week': applications.filter(
                status='approved',
                review_date__date__gte=week_ago
            ).count(),
            'rejected_this_week': applications.filter(
                status='rejected',
                review_date__date__gte=week_ago
            ).count(),
        }
        
        # Get recent applications for the table (with pagination handled via AJAX)
        recent_applications = applications.order_by('-submitted_at')[:20]
        
        # Get available field agents (surveyors)
        field_agents = User.objects.filter(
            role='surveyor', 
            is_active=True
        ).order_by('first_name', 'last_name')
        
        context.update({
            'stats': stats,
            'recent_applications': recent_applications,
            'field_agents': field_agents,
            'today': today,
        })
        
        return context  


@login_required
@require_http_methods(["GET"])
def applications_api_list(request):
    """API endpoint for fetching applications with filtering and pagination"""
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get query parameters
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    app_id = request.GET.get('app_id', '')
    
    # Base queryset
    applications = ParcelApplication.objects.select_related(
        'applicant', 'field_agent', 'reviewed_by'
    ).prefetch_related('documents')
    
    # Single application lookup
    if app_id:
        try:
            app = applications.get(pk=app_id)
            return JsonResponse({
                'success': True,
                'application': {
                    'id': app.id,
                    'application_number': app.application_number,
                    'owner_first_name': app.owner_first_name,
                    'owner_last_name': app.owner_last_name,
                    'property_address': app.property_address,
                    'property_type': app.property_type,
                    'application_type': app.application_type,
                    'application_type_display': app.get_application_type_display(),
                    'status': app.status,
                    'status_display': app.get_status_display(),
                    'submitted_at': app.submitted_at.strftime('%Y-%m-%d'),
                    'applicant_email': app.applicant.email,
                    'document_count': app.documents.count(),
                }
            })
        except ParcelApplication.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Application not found'
            }, status=404)
    
    # Apply filters
    if search:
        applications = applications.filter(
            Q(application_number__icontains=search) |
            Q(owner_first_name__icontains=search) |
            Q(owner_last_name__icontains=search) |
            Q(property_address__icontains=search) |
            Q(applicant__email__icontains=search)
        )
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    if type_filter:
        applications = applications.filter(application_type=type_filter)
    
    if date_from:
        applications = applications.filter(submitted_at__date__gte=date_from)
    
    if date_to:
        applications = applications.filter(submitted_at__date__lte=date_to)
    
    # Add priority logic (based on submission date and urgency)
    applications = applications.order_by('-submitted_at')
    
    # Paginate
    paginator = Paginator(applications, per_page)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    applications_data = []
    for app in page_obj:
        # Calculate priority based on age and complexity
        days_old = (timezone.now().date() - app.submitted_at.date()).days
        priority = 'low'
        if days_old > 7:
            priority = 'urgent'
        elif days_old > 3:
            priority = 'high'
        elif app.application_type == 'parcel_certificate':
            priority = 'medium'
        
        # Get document count
        doc_count = app.documents.count()
        
        applications_data.append({
            'id': app.id,
            'application_number': app.application_number,
            'applicant_name': f"{app.owner_first_name} {app.owner_last_name}",
            'applicant_email': app.applicant.email,
            'property_address': app.property_address,
            'property_type': app.property_type,
            'application_type': app.application_type,
            'application_type_display': app.get_application_type_display(),
            'status': app.status,
            'status_display': app.get_status_display(),
            'priority': priority,
            'submitted_at': app.submitted_at.strftime('%Y-%m-%d'),
            'days_old': days_old,
            'field_agent': app.field_agent.get_full_name() if app.field_agent else None,
            'reviewed_by': app.reviewed_by.get_full_name() if app.reviewed_by else None,
            'document_count': doc_count,
        })
    
    return JsonResponse({
        'success': True,
        'applications': applications_data,
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'per_page': per_page,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
        }
    })


@login_required
@require_POST
def assign_field_agent_bulk(request):
    """Bulk assign field agents to multiple applications"""
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        application_ids = data.get('application_ids', [])
        agent_id = data.get('agent_id')
        priority = data.get('priority', 'normal')
        deadline = data.get('deadline')
        notes = data.get('notes', '')
        
        if not application_ids or not agent_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get the field agent
        field_agent = get_object_or_404(User, id=agent_id, role='surveyor')
        
        # Update applications
        applications = ParcelApplication.objects.filter(
            id__in=application_ids,
            status='submitted'
        )
        
        updated_count = 0
        notifications_to_create = []
        
        with transaction.atomic():
            for app in applications:
                app.field_agent = field_agent
                app.status = 'field_inspection'
                if notes:
                    if app.review_notes:
                        app.review_notes += f"\n\nBulk Assignment Note: {notes}"
                    else:
                        app.review_notes = f"Bulk Assignment Note: {notes}"
                app.save()
                
                # Create notifications for the surveyor
                notifications_to_create.append(
                    Notification(
                        recipient=field_agent,
                        title='New Field Inspection Assignment',
                        message=f'You have been assigned to inspect application {app.application_number}',
                        notification_type='approval_required',
                        priority=priority,
                        sender=request.user
                    )
                )
                
                # Create notifications for applicants
                notifications_to_create.append(
                    Notification(
                        recipient=app.applicant,
                        title='Field Agent Assigned',
                        message=f'Field agent {field_agent.get_full_name()} has been assigned to inspect your application {app.application_number}',
                        notification_type='application_status',
                        sender=request.user
                    )
                )
                
                updated_count += 1
            
            # Bulk create all notifications
            Notification.objects.bulk_create(notifications_to_create)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully assigned {updated_count} applications to {field_agent.get_full_name()}',
            'updated_count': updated_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@require_POST
def quick_application_review(request, application_id):
    """Quick review action for applications"""
    if request.user.role not in ['registry_officer', 'admin', 'surveyor']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    application = get_object_or_404(ParcelApplication, pk=application_id)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'approve', 'reject', 'assign'
        notes = data.get('notes', '')
        
        with transaction.atomic():
            if action == 'approve':
                # Quick approve - ensure we use 'approved' not 'approve'
                application.status = 'approved'
                application.review_notes = notes
                application.review_date = timezone.now()
                application.reviewed_by = request.user
                application.save()
                
                # Get values with proper None handling
                size_hectares = application.size_hectares if application.size_hectares is not None else 1.0
                latitude = application.latitude if application.latitude is not None else -1.9441
                longitude = application.longitude if application.longitude is not None else 30.0619
                
                # Create basic land parcel
                parcel = LandParcel.objects.create(
                    owner=application.applicant,
                    location=application.property_address,
                    property_type=application.property_type,
                    district='North Kivu',
                    sector='Default Sector',
                    cell='Default Cell',
                    village='Default Village',
                    size_hectares=float(size_hectares),
                    latitude=float(latitude),
                    longitude=float(longitude),
                    status='registered',
                    registration_date=timezone.now(),
                    registered_by=request.user
                )
                
                # Link parcel to application
                application.parcel = parcel
                application.save()
                
                # Create title
                expiry_date = None
                if application.application_type == 'property_contract':
                    expiry_date = timezone.now().date() + timezone.timedelta(days=3*365)
                
                title = ParcelTitle.objects.create(
                    parcel=parcel,
                    owner=application.applicant,
                    application=application,
                    title_type=application.application_type,
                    expiry_date=expiry_date,
                    is_active=True
                )
                
                # Set active title on parcel
                parcel.active_title_type = application.application_type
                if application.application_type == 'property_contract':
                    parcel.active_title_expiry = title.expiry_date
                parcel.save()
                
                # Create notification for applicant
                Notification.objects.create(
                    recipient=application.applicant,
                    title='Application Approved',
                    message=f'Your application {application.application_number} has been approved via quick review',
                    notification_type='application_status',
                    priority='high',
                    related_parcel=parcel,
                    sender=request.user
                )
                
                message = 'Application approved and title issued'
                
            elif action == 'reject':
                application.status = 'rejected'
                application.review_notes = notes
                application.review_date = timezone.now()
                application.reviewed_by = request.user
                application.save()
                
                # Create notification for applicant
                Notification.objects.create(
                    recipient=application.applicant,
                    title='Application Rejected',
                    message=f'Your application {application.application_number} has been rejected',
                    notification_type='application_status',
                    sender=request.user
                )
                
                message = 'Application rejected'
                
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action'
                }, status=400)
                
            return JsonResponse({
                'success': True,
                'message': message
            })
            
    except Exception as e:
        print(f"Error in quick review: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error processing review: {str(e)}'
        }, status=500)


@login_required
def export_applications(request):
    """Export applications to CSV"""
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    applications = ParcelApplication.objects.select_related(
        'applicant', 'field_agent', 'reviewed_by'
    ).order_by('-submitted_at')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if type_filter:
        applications = applications.filter(application_type=type_filter)
    if date_from:
        applications = applications.filter(submitted_at__date__gte=date_from)
    if date_to:
        applications = applications.filter(submitted_at__date__lte=date_to)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="applications_export_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Application Number',
        'Applicant Name',
        'Applicant Email',
        'Property Address',
        'Property Type',
        'Application Type',
        'Status',
        'Field Agent',
        'Reviewed By',
        'Submitted Date',
        'Review Date',
        'Review Notes'
    ])
    
    for app in applications:
        writer.writerow([
            app.application_number,
            f"{app.owner_first_name} {app.owner_last_name}",
            app.applicant.email,
            app.property_address,
            app.property_type,
            app.get_application_type_display(),
            app.get_status_display(),
            app.field_agent.get_full_name() if app.field_agent else '',
            app.reviewed_by.get_full_name() if app.reviewed_by else '',
            app.submitted_at.strftime('%Y-%m-%d %H:%M'),
            app.review_date.strftime('%Y-%m-%d %H:%M') if app.review_date else '',
            app.review_notes or ''
        ])
    
    return response



@login_required
def application_analytics(request):
    """Get analytics data for applications dashboard"""
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Time-based analytics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    applications = ParcelApplication.objects.all()
    
    # Status distribution
    status_counts = applications.values('status').annotate(count=Count('id'))
    status_data = {item['status']: item['count'] for item in status_counts}
    
    # Type distribution
    type_counts = applications.values('application_type').annotate(count=Count('id'))
    type_data = {item['application_type']: item['count'] for item in type_counts}
    
    # Timeline data (last 30 days)
    timeline_data = []
    for i in range(30):
        date = today - timedelta(days=i)
        daily_count = applications.filter(submitted_at__date=date).count()
        timeline_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': daily_count
        })
    
    # Performance metrics
    avg_processing_time = applications.filter(
        status__in=['approved', 'rejected'],
        review_date__isnull=False
    ).extra(
        select={'processing_days': 'EXTRACT(days FROM review_date - submitted_at)'}
    ).aggregate(avg_days=Avg('processing_days'))['avg_days'] or 0
    
    # Agent workload
    agent_workload = applications.filter(
        field_agent__isnull=False,
        status='field_inspection'
    ).values(
        'field_agent__first_name',
        'field_agent__last_name'
    ).annotate(
        workload=Count('id')
    ).order_by('-workload')
    
    return JsonResponse({
        'success': True,
        'analytics': {
            'status_distribution': status_data,
            'type_distribution': type_data,
            'timeline_data': timeline_data[::-1],  # Reverse to get chronological order
            'avg_processing_time': round(avg_processing_time, 1),
            'agent_workload': list(agent_workload),
            'summary': {
                'total_applications': applications.count(),
                'this_week': applications.filter(submitted_at__date__gte=week_ago).count(),
                'this_month': applications.filter(submitted_at__date__gte=month_ago).count(),
                'approval_rate': round(
                    applications.filter(status='approved').count() / 
                    max(applications.count(), 1) * 100, 1
                ),
            }
        }
    })


class ApplicationDetailReviewView(RoleRequiredMixin, LoginRequiredMixin, DetailView):
    """Detailed review view for individual applications"""
    allowed_roles = ['registry_officer', 'admin', 'surveyor']
    model = ParcelApplication
    template_name = 'applications/detailed_review.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add documents
        context['documents'] = self.object.documents.all()
        
        # Add forms based on user role and application status
        if (self.request.user.role in ['registry_officer', 'admin'] and 
            self.object.status == 'submitted'):
            context['assignment_form'] = ApplicationAssignmentForm()
        
        if (self.request.user.role in ['surveyor', 'admin'] and 
            self.object.field_agent == self.request.user and 
            self.object.status == 'field_inspection'):
            context['review_form'] = ApplicationReviewForm()
        
        # Add available field agents
        context['field_agents'] = User.objects.filter(
            role='surveyor', 
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # Add application history/timeline
        context['timeline'] = self._get_application_timeline()
        
        return context
    
    def _get_application_timeline(self):
        """Generate timeline events for the application"""
        timeline = []
        app = self.object
        
        # Submitted event
        timeline.append({
            'date': app.submitted_at,
            'event': 'Application Submitted',
            'description': f'Submitted by {app.applicant.get_full_name()}',
            'icon': 'fas fa-file-upload',
            'color': 'blue'
        })
        
        # Field agent assigned
        if app.field_agent:
            timeline.append({
                'date': app.updated_at,  # You might want to track this separately
                'event': 'Field Agent Assigned',
                'description': f'Assigned to {app.field_agent.get_full_name()}',
                'icon': 'fas fa-user-plus',
                'color': 'green'
            })
        
        # Review completed
        if app.review_date:
            timeline.append({
                'date': app.review_date,
                'event': 'Review Completed',
                'description': f'Reviewed by {app.reviewed_by.get_full_name()}' if app.reviewed_by else 'Review completed',
                'icon': 'fas fa-clipboard-check',
                'color': 'green' if app.status == 'approved' else 'red'
            })
        
        return sorted(timeline, key=lambda x: x['date'])


@login_required
@require_POST 
def change_application_priority(request):
    """Change priority for multiple applications"""
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        application_ids = data.get('application_ids', [])
        priority = data.get('priority', 'normal')
        
        if not application_ids:
            return JsonResponse({'error': 'No applications selected'}, status=400)
        
        # For now, we'll store priority in review_notes or create a separate field
        # In a production system, you'd want a dedicated priority field
        applications = ParcelApplication.objects.filter(id__in=application_ids)
        
        updated_count = 0
        with transaction.atomic():
            for app in applications:
                # Add priority note
                priority_note = f"Priority set to {priority.upper()} by {request.user.get_full_name()}"
                if app.review_notes:
                    app.review_notes += f"\n{priority_note}"
                else:
                    app.review_notes = priority_note
                app.save()
                updated_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Updated priority for {updated_count} applications',
            'updated_count': updated_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def application_comments(request, application_id):
    """Handle comments/notes for applications"""
    if request.user.role not in ['registry_officer', 'admin', 'surveyor']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    application = get_object_or_404(ParcelApplication, id=application_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            comment = data.get('comment', '').strip()
            
            if not comment:
                return JsonResponse({'error': 'Comment cannot be empty'}, status=400)
            
            # Add comment to review notes with timestamp and user
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
            new_comment = f"[{timestamp}] {request.user.get_full_name()}: {comment}"
            
            if application.review_notes:
                application.review_notes += f"\n{new_comment}"
            else:
                application.review_notes = new_comment
            
            application.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Comment added successfully',
                'comment': {
                    'text': comment,
                    'author': request.user.get_full_name(),
                    'timestamp': timestamp
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - return existing comments
    comments = []
    if application.review_notes:
        # Parse comments from review_notes
        lines = application.review_notes.split('\n')
        for line in lines:
            if line.strip().startswith('['):
                # Parse timestamp and author
                try:
                    parts = line.split('] ', 1)
                    if len(parts) == 2:
                        timestamp_part = parts[0][1:]  # Remove opening bracket
                        content_part = parts[1]
                        
                        if ': ' in content_part:
                            author, text = content_part.split(': ', 1)
                            comments.append({
                                'timestamp': timestamp_part,
                                'author': author,
                                'text': text
                            })
                except:
                    continue
    
    return JsonResponse({
        'success': True,
        'comments': comments
    })


@login_required
def applications_workload_distribution(request):
    """Get workload distribution for field agents"""
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get all surveyors
    surveyors = User.objects.filter(role='surveyor', is_active=True)
    
    workload_data = []
    for surveyor in surveyors:
        # Count active assignments
        active_inspections = ParcelApplication.objects.filter(
            field_agent=surveyor,
            status='field_inspection'
        ).count()
        
        # Count completed inspections this month
        month_ago = timezone.now() - timedelta(days=30)
        completed_this_month = ParcelApplication.objects.filter(
            field_agent=surveyor,
            status__in=['approved', 'rejected'],
            review_date__gte=month_ago
        ).count()
        
        workload_data.append({
            'id': surveyor.id,
            'name': surveyor.get_full_name(),
            'email': surveyor.email,
            'active_inspections': active_inspections,
            'completed_this_month': completed_this_month,
            'total_assigned': active_inspections + completed_this_month,
            'availability': 'high' if active_inspections < 3 else 'medium' if active_inspections < 6 else 'low'
        })
    
    # Sort by availability (least busy first)
    workload_data.sort(key=lambda x: x['active_inspections'])
    
    return JsonResponse({
        'success': True,
        'workload_data': workload_data
    })


class ApplicationsReportView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    """Generate comprehensive reports on applications"""
    allowed_roles = ['registry_officer', 'admin']
    template_name = 'applications/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)
        
        applications = ParcelApplication.objects.all()
        
        # Generate comprehensive statistics
        stats = {
            'total_applications': applications.count(),
            'applications_this_week': applications.filter(submitted_at__date__gte=week_ago).count(),
            'applications_this_month': applications.filter(submitted_at__date__gte=month_ago).count(),
            'applications_this_year': applications.filter(submitted_at__date__gte=year_ago).count(),
            
            # Status breakdown
            'submitted': applications.filter(status='submitted').count(),
            'under_review': applications.filter(status='under_review').count(),
            'field_inspection': applications.filter(status='field_inspection').count(),
            'approved': applications.filter(status='approved').count(),
            'rejected': applications.filter(status='rejected').count(),
            
            # Type breakdown
            'property_contracts': applications.filter(application_type='property_contract').count(),
            'parcel_certificates': applications.filter(application_type='parcel_certificate').count(),
            
            # Performance metrics
            'avg_processing_days': self._calculate_avg_processing_time(applications),
            'approval_rate': self._calculate_approval_rate(applications),
        }
        
        # Monthly trends
        monthly_trends = self._get_monthly_trends(applications)
        
        # Top performing agents
        top_agents = self._get_top_performing_agents()
        
        context.update({
            'stats': stats,
            'monthly_trends': monthly_trends,
            'top_agents': top_agents,
        })
        
        return context
    
    def _calculate_avg_processing_time(self, applications):
        """Calculate average processing time in days"""
        processed_apps = applications.filter(
            status__in=['approved', 'rejected'],
            review_date__isnull=False
        )
        
        if not processed_apps.exists():
            return 0
        
        total_days = 0
        count = 0
        
        for app in processed_apps:
            days = (app.review_date.date() - app.submitted_at.date()).days
            total_days += days
            count += 1
        
        return round(total_days / count, 1) if count > 0 else 0
    
    def _calculate_approval_rate(self, applications):
        """Calculate approval rate percentage"""
        total_reviewed = applications.filter(status__in=['approved', 'rejected']).count()
        if total_reviewed == 0:
            return 0
        
        approved = applications.filter(status='approved').count()
        return round((approved / total_reviewed) * 100, 1)
    
    def _get_monthly_trends(self, applications):
        """Get application trends by month for the last 12 months"""
        trends = []
        today = timezone.now().date()
        
        for i in range(12):
            # Calculate the first day of the month
            month_start = today.replace(day=1) - timedelta(days=i*30)
            month_start = month_start.replace(day=1)
            
            # Calculate the last day of the month
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            
            month_apps = applications.filter(
                submitted_at__date__gte=month_start,
                submitted_at__date__lte=month_end
            )
            
            trends.append({
                'month': month_start.strftime('%B %Y'),
                'total': month_apps.count(),
                'approved': month_apps.filter(status='approved').count(),
                'rejected': month_apps.filter(status='rejected').count(),
                'pending': month_apps.filter(status__in=['submitted', 'under_review', 'field_inspection']).count(),
            })
        
        return trends[::-1]  # Reverse to get chronological order
    
    def _get_top_performing_agents(self):
        """Get top performing field agents"""
        month_ago = timezone.now() - timedelta(days=30)
        
        agents = User.objects.filter(role='surveyor', is_active=True)
        agent_performance = []
        
        for agent in agents:
            completed = ParcelApplication.objects.filter(
                field_agent=agent,
                status__in=['approved', 'rejected'],
                review_date__gte=month_ago
            )
            
            approved = completed.filter(status='approved').count()
            total_completed = completed.count()
            
            if total_completed > 0:
                agent_performance.append({
                    'name': agent.get_full_name(),
                    'completed': total_completed,
                    'approved': approved,
                    'approval_rate': round((approved / total_completed) * 100, 1)
                })
        
        # Sort by number of completed applications
        agent_performance.sort(key=lambda x: x['completed'], reverse=True)
        
        return agent_performance[:10]  # Top 10
    

@login_required
@require_POST
def registry_approval(request, application_id):
    """View for registry officers to make final approval/rejection after inspection"""
    print(f"Registry approval called for application {application_id}")
    
    if request.user.role not in ['registry_officer', 'admin']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    application = get_object_or_404(ParcelApplication, pk=application_id)
    
    # Check if application is in the correct state
    if application.status != 'inspection_completed':
        return JsonResponse({
            'success': False,
            'message': f'This application is not ready for final approval. Current status: {application.status}'
        }, status=400)
    
    try:
        data = json.loads(request.body)
        decision = data.get('decision')
        additional_notes = data.get('notes', '')
        
        print(f"Decision: {decision}, Notes: {additional_notes}")
        
        if decision not in ['approve', 'reject']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid decision. Must be either "approve" or "reject".'
            }, status=400)
        
        with transaction.atomic():
            # Update application status
            if decision == 'approve':
                application.status = 'approved'
            elif decision == 'reject':
                application.status = 'rejected'
            
            # Add additional notes from registry officer
            registry_notes = f"Registry Decision ({timezone.now().strftime('%Y-%m-%d')}): {additional_notes}"
            if application.review_notes:
                application.review_notes += f"\n\n{registry_notes}"
            else:
                application.review_notes = registry_notes
            
            # Save the application with updated status
            application.reviewed_by = request.user
            application.review_date = timezone.now()
            application.save()
            
            print(f"Application status updated to: {application.status}")
            
            # If approved, create land parcel and title
            parcel = None
            title = None
            if decision == 'approve':
                # Generate a unique parcel ID
                parcel_id = f"PCL-{application.application_number}"
                
                try:
                    # Check if parcel already exists
                    existing_parcel = LandParcel.objects.filter(parcel_id=parcel_id).first()
                    if existing_parcel:
                        parcel_id = f"PCL-{application.application_number}-{int(timezone.now().timestamp())}"
                    
                    # Get boundary data if it exists
                    boundary = None
                    try:
                        from land_management.models import ParcelBoundary
                        boundary = ParcelBoundary.objects.filter(application=application).first()
                        print(f"Boundary found: {boundary is not None}")
                    except Exception as e:
                        print(f"Could not retrieve boundary: {e}")
                    
                    # Get coordinates and size - prefer boundary data, then application data, then defaults
                    if boundary:
                        # Use boundary data if available
                        latitude = float(boundary.center_lat) if boundary.center_lat else -1.9441
                        longitude = float(boundary.center_lng) if boundary.center_lng else 30.0619
                        size_hectares = float(boundary.area_hectares) if boundary.area_hectares else 1.0
                    else:
                        # Fall back to application data
                        latitude = float(application.latitude) if application.latitude else -1.9441
                        longitude = float(application.longitude) if application.longitude else 30.0619
                        size_hectares = float(application.size_hectares) if application.size_hectares else 1.0
                    
                    print(f"Coordinates: lat={latitude}, lng={longitude}, size={size_hectares}")
                    
                    # Extract location details from property address
                    property_parts = application.property_address.split(',') if application.property_address else []
                    
                    # Map property_type string to valid LandParcel choices
                    property_type_text = application.property_type.lower() if application.property_type else 'residential'
                    
                    # Create mapping for common property types
                    property_type_map = {
                        'residential': 'residential',
                        'commercial': 'commercial',
                        'agricultural': 'agricultural',
                        'industrial': 'industrial',
                        'mixed': 'mixed',
                        'mixed use': 'mixed',
                        'agriculture': 'agricultural',
                        'residence': 'residential',
                        'commerce': 'commercial',
                        'industry': 'industrial'
                    }
                    
                    # Get the mapped property type or default to residential
                    property_type = property_type_map.get(property_type_text, 'residential')
                    
                    print(f"Creating parcel with property_type: {property_type}")
                    
                    # Create land parcel
                    parcel = LandParcel(
                        parcel_id=parcel_id,
                        owner=application.applicant,
                        location=application.property_address,
                        property_type=property_type,
                        district=property_parts[1].strip() if len(property_parts) > 1 else 'Kigali',
                        sector=property_parts[2].strip() if len(property_parts) > 2 else 'Default Sector',
                        cell=property_parts[3].strip() if len(property_parts) > 3 else 'Default Cell',
                        village=property_parts[4].strip() if len(property_parts) > 4 else 'Default Village',
                        size_hectares=size_hectares,
                        latitude=latitude,
                        longitude=longitude,
                        status='registered',
                        registration_date=timezone.now(),
                        registered_by=request.user
                    )
                    parcel.save()
                    
                    print(f"Parcel created: {parcel.parcel_id}")
                    
                    # Link parcel to application
                    application.parcel = parcel
                    application.save()
                    
                    # Determine title type and expiry
                    title_type = application.application_type
                    expiry_date = None
                    if title_type == 'property_contract':
                        expiry_date = timezone.now().date() + timezone.timedelta(days=3*365)  # 3 years
                    
                    # Create parcel title
                    title = ParcelTitle.objects.create(
                        parcel=parcel,
                        owner=application.applicant,
                        application=application,
                        title_type=title_type,
                        expiry_date=expiry_date,
                        is_active=True
                    )
                    
                    # Update parcel with active title information
                    parcel.active_title_type = title_type
                    if title_type == 'property_contract':
                        parcel.active_title_expiry = expiry_date
                    parcel.save()
                    
                    print(f"Title created: {title.title_number}")
                    
                except Exception as e:
                    print(f"Error creating parcel/title: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    # Return error but keep the application status updated
                    return JsonResponse({
                        'success': False,
                        'message': f'Application approved but failed to create parcel/title: {str(e)}'
                    }, status=500)
            
            # Create notifications for all parties
            notifications_to_create = []
            
            # 1. Notify the applicant
            if decision == 'approve':
                message = f'Congratulations! Your application {application.application_number} has been approved.'
                if title:
                    message += f' Title {title.title_number} has been issued.'
                
                notifications_to_create.append(
                    Notification(
                        recipient=application.applicant,
                        title='Application Approved',
                        message=message,
                        notification_type='application_status',
                        priority='high',
                        related_parcel=parcel,
                        sender=request.user
                    )
                )
            else:
                notifications_to_create.append(
                    Notification(
                        recipient=application.applicant,
                        title='Application Rejected',
                        message=f'Your application {application.application_number} has been rejected. Reason: {additional_notes}',
                        notification_type='application_status',
                        priority='high',
                        sender=request.user
                    )
                )
            
            # 2. Notify field agent who did the inspection
            if application.field_agent:
                notifications_to_create.append(
                    Notification(
                        recipient=application.field_agent,
                        title=f'Application {decision.capitalize()}d',
                        message=f'Application {application.application_number} that you inspected has been {decision}d by registry.',
                        notification_type='application_status',
                        sender=request.user
                    )
                )
            
            # Bulk create notifications
            if notifications_to_create:
                Notification.objects.bulk_create(notifications_to_create)
            
            # Prepare success response
            response_message = f'Application successfully {decision}d!'
            if decision == 'approve' and parcel and title:
                response_message += f' Parcel {parcel.parcel_id} and Title {title.title_number} created.'
            
            return JsonResponse({
                'success': True,
                'message': response_message,
                'application_id': application.id,
                'new_status': application.status,
                'parcel_id': parcel.parcel_id if parcel else None,
                'title_number': title.title_number if title else None
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        print(f"Unexpected error in registry_approval: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }, status=500)