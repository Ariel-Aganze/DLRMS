from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages

class RoleRequiredMixin(LoginRequiredMixin):
    """Mixin that requires user to have specific role(s)"""
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if self.allowed_roles and request.user.role not in self.allowed_roles:
            messages.error(request, 'You do not have permission to access this page.')
            raise PermissionDenied
        
        return super().dispatch(request, *args, **kwargs)

class LandownerRequiredMixin(RoleRequiredMixin):
    """Mixin for landowner-only views"""
    allowed_roles = ['landowner']

class OfficerRequiredMixin(RoleRequiredMixin):
    """Mixin for registry officer views"""
    allowed_roles = ['registry_officer', 'admin']

class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin for admin-only views"""
    allowed_roles = ['admin']

class SurveyorRequiredMixin(RoleRequiredMixin):
    """Mixin for surveyor views"""
    allowed_roles = ['surveyor', 'admin']

class NotaryRequiredMixin(RoleRequiredMixin):
    """Mixin for notary views"""
    allowed_roles = ['notary', 'admin']