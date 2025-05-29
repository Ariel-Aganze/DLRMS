from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles):
    """
    Decorator that checks if user has one of the allowed roles
    Usage: @role_required(['registry_officer', 'admin'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if request.user.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                raise PermissionDenied
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def landowner_required(view_func):
    """Decorator for landowner-only views"""
    return role_required(['landowner'])(view_func)

def officer_required(view_func):
    """Decorator for registry officer views"""
    return role_required(['registry_officer', 'admin'])(view_func)

def admin_required(view_func):
    """Decorator for admin-only views"""
    return role_required(['admin'])(view_func)

def surveyor_required(view_func):
    """Decorator for surveyor views"""
    return role_required(['surveyor', 'admin'])(view_func)

def notary_required(view_func):
    """Decorator for notary views"""
    return role_required(['notary', 'admin'])(view_func)