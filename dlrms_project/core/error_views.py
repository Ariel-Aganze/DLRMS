# core/error_views.py
from django.shortcuts import render
import logging
from django.conf import settings

# Configure logger
logger = logging.getLogger(__name__)

def handler403(request, exception=None):
    """
    Custom 403 (Permission Denied) error handler
    """
    logger.warning(
        f"403 Forbidden: {request.path}",
        extra={
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
            'ip': request.META.get('REMOTE_ADDR'),
            'referrer': request.META.get('HTTP_REFERER', 'None')
        }
    )
    # Context with DEBUG setting to avoid static file issues
    context = {
        'debug': settings.DEBUG,
    }
    return render(request, 'errors/403.html', context, status=403)

def handler404(request, exception=None):
    """
    Custom 404 (Page Not Found) error handler
    """
    logger.warning(
        f"404 Not Found: {request.path}",
        extra={
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
            'ip': request.META.get('REMOTE_ADDR'),
            'referrer': request.META.get('HTTP_REFERER', 'None')
        }
    )
    # Add context with DEBUG setting to avoid static file issues
    context = {
        'debug': settings.DEBUG,
    }
    return render(request, 'errors/404.html', context, status=404)

def handler500(request):
    """
    Custom 500 (Server Error) error handler
    """
    logger.error(
        f"500 Server Error: {request.path}",
        extra={
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
            'ip': request.META.get('REMOTE_ADDR'),
        }
    )
    # Add context with DEBUG setting to avoid static file issues
    context = {
        'debug': settings.DEBUG,
    }
    return render(request, 'errors/500.html', context, status=500)