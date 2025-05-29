# core/admin_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from .decorators import admin_required, officer_required
import csv
from django.http import HttpResponse

User = get_user_model()

@login_required
@officer_required
@require_POST
def verify_user(request, user_id):
    """Verify a user (AJAX endpoint)"""
    try:
        user = get_object_or_404(User, id=user_id)
        user.is_verified = True
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'User {user.username} has been verified successfully.',
            'user_id': user_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error verifying user: {str(e)}'
        }, status=400)

@login_required
@officer_required
@require_POST
def toggle_user_active(request, user_id):
    """Toggle user active status (AJAX endpoint)"""
    try:
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        
        action = "activated" if user.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'User {user.username} has been {action} successfully.',
            'user_id': user_id,
            'is_active': user.is_active
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling user status: {str(e)}'
        }, status=400)

@login_required
@officer_required
@require_POST
def bulk_verify_users(request):
    """Bulk verify all unverified users (AJAX endpoint)"""
    try:
        unverified_users = User.objects.filter(is_verified=False)
        count = unverified_users.count()
        
        if count == 0:
            return JsonResponse({
                'success': True,
                'message': 'No unverified users found.',
                'count': 0
            })
        
        unverified_users.update(is_verified=True)
        
        return JsonResponse({
            'success': True,
            'message': f'{count} users have been verified successfully.',
            'count': count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error in bulk verification: {str(e)}'
        }, status=400)

@login_required
@officer_required
def export_users(request):
    """Export users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dlrms_users.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'First Name', 'Last Name', 'Email', 'Role', 
        'Phone Number', 'National ID', 'Is Verified', 'Is Active', 
        'Date Joined', 'Last Login'
    ])
    
    users = User.objects.all().order_by('-date_joined')
    for user in users:
        writer.writerow([
            user.username,
            user.first_name,
            user.last_name,
            user.email,
            user.get_role_display(),
            user.phone_number or '',
            user.national_id or '',
            'Yes' if user.is_verified else 'No',
            'Yes' if user.is_active else 'No',
            user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
        ])
    
    return response

@login_required
@officer_required
def get_user_stats(request):
    """Get updated user statistics (AJAX endpoint)"""
    try:
        all_users = User.objects.all()
        
        stats = {
            'total_users': all_users.count(),
            'verified_users': all_users.filter(is_verified=True).count(),
            'unverified_users': all_users.filter(is_verified=False).count(),
            'active_users': all_users.filter(is_active=True).count(),
            'inactive_users': all_users.filter(is_active=False).count(),
            'total_landowners': all_users.filter(role='landowner').count(),
            'total_officers': all_users.filter(
                role__in=['registry_officer', 'surveyor', 'notary', 'admin']
            ).count(),
            'new_users_today': all_users.filter(
                date_joined__date=timezone.now().date()
            ).count(),
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching stats: {str(e)}'
        }, status=400)

@login_required
@officer_required
def search_users(request):
    """Search users (AJAX endpoint)"""
    try:
        query = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role', '').strip()
        status_filter = request.GET.get('status', '').strip()
        
        users = User.objects.all()
        
        if query:
            users = users.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(national_id__icontains=query)
            )
        
        if role_filter:
            users = users.filter(role=role_filter)
        
        if status_filter == 'verified':
            users = users.filter(is_verified=True)
        elif status_filter == 'unverified':
            users = users.filter(is_verified=False)
        elif status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
        
        users = users.order_by('-date_joined')[:50]  # Limit to 50 results
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
                'is_verified': user.is_verified,
                'is_active': user.is_active,
                'date_joined': user.date_joined.strftime('%Y-%m-%d'),
                'last_login': user.last_login.strftime('%Y-%m-%d') if user.last_login else None,
            })
        
        return JsonResponse({
            'success': True,
            'users': users_data,
            'count': len(users_data)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error searching users: {str(e)}'
        }, status=400)