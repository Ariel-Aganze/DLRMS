from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import CustomUserRegistrationForm, CustomLoginForm, UserProfileForm

User = get_user_model()

class RegisterView(CreateView):
    """User registration view - automatically creates landowner accounts"""
    model = User
    form_class = CustomUserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('core:dashboard')
    
    def form_valid(self, form):
        """Automatically log in user after successful registration"""
        response = super().form_valid(form)
        
        # Log the user in
        login(self.request, self.object)
        
        # Add success message
        messages.success(
            self.request, 
            f'Welcome to DLRMS, {self.object.first_name}! Your landowner account has been created successfully. '
            f'You can now register your land parcels and manage your property documentation.'
        )
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Register - DLRMS'
        return context


class LoginView(AuthLoginView):
    """Custom login view"""
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirect based on user role"""
        user = self.request.user
        if user.role in ['registry_officer', 'admin']:
            return reverse_lazy('core:dashboard')  # Admin dashboard
        else:
            return reverse_lazy('core:dashboard')  # User dashboard
    
    def form_valid(self, form):
        """Add success message on login"""
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {self.request.user.first_name}!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login - DLRMS'
        return context


class LogoutView(AuthLogoutView):
    """Custom logout view"""
    next_page = reverse_lazy('core:home')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, UpdateView):
    """User profile view"""
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        """Return the current user"""
        return self.request.user
    
    def form_valid(self, form):
        """Add success message on profile update"""
        response = super().form_valid(form)
        messages.success(self.request, 'Your profile has been updated successfully.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Profile - DLRMS'
        
        # Add user statistics
        user = self.request.user
        context['user_stats'] = {
            'total_parcels': user.land_parcels.count(),
            'total_applications': user.applications.count(),
            'pending_applications': user.applications.filter(status='submitted').count(),
            'total_disputes': user.filed_disputes.count(),
        }
        return context