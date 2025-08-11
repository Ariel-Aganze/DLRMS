# core/admin_views.py
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from .decorators import admin_required, officer_required
import csv
import logging

# Set up logging
logger = logging.getLogger(__name__)

User = get_user_model()


@login_required
@officer_required
@require_POST
def create_user(request):
    """Create a new user (AJAX endpoint)"""
    try:
        logger.info(f"User creation request from {request.user.username}")
        
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        phone_number = request.POST.get('phone_number', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        address = request.POST.get('address', '').strip()
        is_verified = request.POST.get('is_verified') == 'on'
        
        logger.info(f"Creating user: {username}, {email}, {role}")
        
        # Validation
        if not all([username, email, first_name, last_name, role, password1, password2]):
            return JsonResponse({
                'success': False,
                'message': 'All required fields must be filled.'
            }, status=400)
        
        if password1 != password2:
            return JsonResponse({
                'success': False,
                'message': 'Passwords do not match.'
            }, status=400)
        
        if len(password1) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password must be at least 8 characters long.'
            }, status=400)
        
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username already exists.'
            }, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'Email already exists.'
            }, status=400)
        
        # Check if national_id already exists (if provided)
        if national_id and User.objects.filter(national_id=national_id).exists():
            return JsonResponse({
                'success': False,
                'message': 'National ID already exists.'
            }, status=400)
        
        # FIXED: Validate role permissions - now includes dispute_officer
        # Dynamically get valid roles from the User model
        valid_roles = [role_choice[0] for role_choice in User.ROLE_CHOICES]
        
        # Non-admin users cannot create admin users
        if request.user.role != 'admin' and role == 'admin':
            return JsonResponse({
                'success': False,
                'message': 'Only administrators can create admin users.'
            }, status=403)
        
        if role not in valid_roles:
            return JsonResponse({
                'success': False,
                'message': f'Invalid role selected. Valid roles are: {", ".join(valid_roles)}'
            }, status=400)
        
        # Create the user
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone_number=phone_number or None,
            national_id=national_id or None,
            address=address or None,
            is_verified=is_verified,
            password=make_password(password1)
        )
        
        logger.info(f"User {username} created successfully with role {role}")
        
        return JsonResponse({
            'success': True,
            'message': f'User {username} created successfully.',
            'user_id': user.id
        })
    
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error creating user: {str(e)}'
        }, status=500)

@login_required
@officer_required
def get_user(request, user_id):
    """Get user data for editing (AJAX endpoint)"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': user.role,
            'phone_number': user.phone_number,
            'national_id': user.national_id,
            'address': user.address,
            'is_verified': user.is_verified,
            'is_active': user.is_active,
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'last_login': user.last_login.strftime('%Y-%m-%d') if user.last_login else None,
        }
        
        return JsonResponse({
            'success': True,
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error fetching user: {str(e)}'
        }, status=500)


@login_required
@officer_required
@require_POST
def update_user(request):
    """Update user data (AJAX endpoint)"""
    try:
        user_id = request.POST.get('user_id')
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'User ID is required.'
            }, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        address = request.POST.get('address', '').strip()
        is_verified = request.POST.get('is_verified') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        reset_password = request.POST.get('reset_password') == 'on'
        
        # Validation
        if not all([username, email, first_name, last_name, role]):
            return JsonResponse({
                'success': False,
                'message': 'All required fields must be filled.'
            }, status=400)
        
        # Check if username or email already exists (excluding current user)
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username already exists.'
            }, status=400)
        
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            return JsonResponse({
                'success': False,
                'message': 'Email already exists.'
            }, status=400)
        
        # Check if national_id already exists (if provided and excluding current user)
        if national_id and User.objects.filter(national_id=national_id).exclude(id=user_id).exists():
            return JsonResponse({
                'success': False,
                'message': 'National ID already exists.'
            }, status=400)
        
        # FIXED: Validate role permissions - now includes dispute_officer
        # Dynamically get valid roles from the User model
        valid_roles = [role_choice[0] for role_choice in User.ROLE_CHOICES]
        
        # Non-admin users cannot assign admin role
        if request.user.role != 'admin' and role == 'admin':
            return JsonResponse({
                'success': False,
                'message': 'Only administrators can assign the admin role.'
            }, status=403)
        
        # Prevent users from changing their own role to admin (security measure)
        if user_id == str(request.user.id) and role == 'admin' and request.user.role != 'admin':
            return JsonResponse({
                'success': False,
                'message': 'You cannot change your own role to admin.'
            }, status=403)
        
        if role not in valid_roles:
            return JsonResponse({
                'success': False,
                'message': f'Invalid role selected. Valid roles are: {", ".join(valid_roles)}'
            }, status=400)
        
        # Update the user
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.phone_number = phone_number or None
        user.national_id = national_id or None
        user.address = address or None
        user.is_verified = is_verified
        user.is_active = is_active
        
        # Handle password reset
        password_message = ''
        if reset_password:
            import secrets
            import string
            # Generate a secure random password
            new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            user.password = make_password(new_password)
            
            # In a real implementation, you would send this password via email
            # For now, we'll return it in the response (not recommended for production)
            password_message = f' New password: {new_password} (Please send this to the user securely)'
            
            logger.info(f"Password reset for user {username}")
        
        user.save()
        
        logger.info(f"User {username} updated successfully with role {role}")
        
        return JsonResponse({
            'success': True,
            'message': f'User {username} updated successfully.{password_message}',
            'user_id': user.id
        })
        
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error updating user: {str(e)}'
        }, status=500)

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
        logger.error(f"Error verifying user {user_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error verifying user: {str(e)}'
        }, status=500)

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
        logger.error(f"Error toggling user {user_id} status: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error toggling user status: {str(e)}'
        }, status=500)

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
        logger.error(f"Error in bulk verification: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error in bulk verification: {str(e)}'
        }, status=500)

@login_required
@officer_required
def export_users(request):
    """Export users to CSV"""
    try:
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
    except Exception as e:
        logger.error(f"Error exporting users: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error exporting users: {str(e)}'
        }, status=500)

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
        logger.error(f"Error fetching stats: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error fetching stats: {str(e)}'
        }, status=500)

@login_required
@officer_required
def search_users(request):
    """Search users with pagination (AJAX endpoint)"""
    try:
        query = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role', '').strip()
        status_filter = request.GET.get('status', '').strip()
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
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
        
        # Get total count before pagination
        total_count = users.count()
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        # Apply pagination
        users = users.order_by('-date_joined')[start_index:end_index]
        
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
        
        # Calculate pagination info
        start_record = start_index + 1 if total_count > 0 else 0
        end_record = min(end_index, total_count)
        
        return JsonResponse({
            'success': True,
            'users': users_data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'per_page': per_page,
                'start': start_record,
                'end': end_record,
                'has_previous': page > 1,
                'has_next': page < total_pages,
            }
        })
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error searching users: {str(e)}'
        }, status=500)