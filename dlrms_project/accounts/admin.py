from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .forms import AdminUserCreationForm

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin for User model"""
    
    add_form = AdminUserCreationForm
    
    # Fields to display in the user list
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'national_id')
    
    # Fields for the user detail/edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'address', 'date_of_birth', 'national_id', 'is_verified')
        }),
    )
    
    # Fields for the add user form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'national_id', 'password1', 'password2', 'is_verified'),
        }),
    )
    
    # Add custom actions
    actions = ['verify_users', 'unverify_users']
    
    def verify_users(self, request, queryset):
        """Mark selected users as verified"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users were successfully verified.')
    verify_users.short_description = "Verify selected users"
    
    def unverify_users(self, request, queryset):
        """Mark selected users as unverified"""
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} users were successfully unverified.')
    unverify_users.short_description = "Unverify selected users"