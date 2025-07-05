from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
import csv
import datetime

from core.models import AuditLog
from certificates.models import CertificateAuditLog
from django.contrib.auth import get_user_model
from .utils import create_sample_audit_logs

User = get_user_model()

def is_admin_or_registry_officer(user):
    return user.role in ['admin', 'registry_officer']

@login_required
@user_passes_test(is_admin_or_registry_officer)
def system_reports_dashboard(request):
    # Check if any audit logs exist
    if AuditLog.objects.count() == 0:
        messages.info(request, "No audit logs found. Use the 'Generate Sample Data' button to create sample logs for testing.")
    
    # Get counts for dashboard metrics
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # System-wide metrics
    total_users = User.objects.count()
    active_users_today = AuditLog.objects.filter(
        timestamp__date=today, 
        action_type='login'
    ).values('user').distinct().count()
    
    # Monthly actions
    monthly_actions = AuditLog.objects.filter(
        timestamp__date__gte=start_of_month
    ).count()
    
    # Action type distribution
    action_counts = AuditLog.objects.values('action_type').annotate(
        count=Count('action_type')
    ).order_by('-count')[:5]
    
    # Recent activity
    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    # Get action types for display
    action_types = dict(AuditLog.ACTION_TYPE_CHOICES)
    
    context = {
        'total_users': total_users,
        'active_users_today': active_users_today,
        'monthly_actions': monthly_actions,
        'action_counts': action_counts,
        'recent_logs': recent_logs,
        'action_types': action_types,
    }
    
    return render(request, 'reports/dashboard.html', context)

@login_required
@user_passes_test(is_admin_or_registry_officer)
def generate_sample_data(request):
    """Generate sample audit logs for testing"""
    logs_created = create_sample_audit_logs()
    messages.success(request, f"Successfully generated {logs_created} sample audit logs.")
    return redirect('reports:dashboard')

@login_required
@user_passes_test(is_admin_or_registry_officer)
def audit_logs_list(request):
    # Get filter parameters
    user_id = request.GET.get('user_id')
    action_type = request.GET.get('action_type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    
    # Apply filters
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)
    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)
    
    # Calculate statistics
    unique_users_count = logs.values('user').distinct().count()
    success_count = logs.filter(success=True).count()
    success_percentage = 0
    if logs.count() > 0:
        success_percentage = int((success_count / logs.count()) * 100)
    
    # Date range for display
    date_range = ""
    if logs.exists():
        oldest_log = logs.order_by('timestamp').first()
        newest_log = logs.order_by('-timestamp').first()
        if oldest_log and newest_log:
            oldest_date = oldest_log.timestamp.strftime('%b %d, %Y')
            newest_date = newest_log.timestamp.strftime('%b %d, %Y')
            if oldest_date != newest_date:
                date_range = f"{oldest_date} to {newest_date}"
            else:
                date_range = oldest_date
    
    # Pagination
    paginator = Paginator(logs, 20)  # Show 20 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For the filter dropdowns
    users = User.objects.all()
    action_types = dict(AuditLog.ACTION_TYPE_CHOICES)
    
    context = {
        'logs': logs,
        'page_obj': page_obj,
        'paginator': paginator,
        'users': users,
        'action_types': action_types,
        'unique_users_count': unique_users_count,
        'success_count': success_count,
        'success_percentage': success_percentage,
        'date_range': date_range,
        'filters': {
            'user_id': user_id,
            'action_type': action_type,
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    
    return render(request, 'reports/audit_logs.html', context)

@login_required
@user_passes_test(is_admin_or_registry_officer)
def certificate_audit_logs(request):
    # Get filter parameters
    user_id = request.GET.get('user_id')
    action = request.GET.get('action')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    logs = CertificateAuditLog.objects.select_related('certificate', 'performed_by').order_by('-timestamp')
    
    # Apply filters
    if user_id:
        logs = logs.filter(performed_by_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)
    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)
    
    # Pagination
    paginator = Paginator(logs, 20)  # Show 20 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For the filter dropdowns
    users = User.objects.all()
    action_types = dict(CertificateAuditLog.ACTION_CHOICES)
    
    # Statistics
    unique_certs_count = logs.values('certificate').distinct().count()
    
    # Date range for display
    date_range = ""
    if logs.exists():
        oldest_log = logs.order_by('timestamp').first()
        newest_log = logs.order_by('-timestamp').first()
        if oldest_log and newest_log:
            oldest_date = oldest_log.timestamp.strftime('%b %d, %Y')
            newest_date = newest_log.timestamp.strftime('%b %d, %Y')
            if oldest_date != newest_date:
                date_range = f"{oldest_date} to {newest_date}"
            else:
                date_range = oldest_date
    
    context = {
        'logs': logs,
        'page_obj': page_obj,
        'paginator': paginator,
        'users': users,
        'action_types': action_types,
        'unique_certs_count': unique_certs_count,
        'date_range': date_range,
        'filters': {
            'user_id': user_id,
            'action': action,
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    
    return render(request, 'reports/certificate_logs.html', context)

@login_required
@user_passes_test(is_admin_or_registry_officer)
def export_audit_logs(request):
    # Export audit logs as CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    # Get filtered logs (similar to audit_logs_list)
    user_id = request.GET.get('user_id')
    action_type = request.GET.get('action_type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    
    # Apply filters
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)
    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Action', 'Description', 'IP Address', 'Success'])
    
    action_types = dict(AuditLog.ACTION_TYPE_CHOICES)
    
    for log in logs:
        action_name = action_types.get(log.action_type, log.action_type)
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else 'System',
            action_name,
            log.description,
            log.ip_address or 'N/A',
            'Yes' if log.success else 'No',
        ])
    
    return response