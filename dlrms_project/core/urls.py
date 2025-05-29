from django.urls import path
from . import views
from . import admin_views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('services/', views.ServicesView.as_view(), name='services'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    
    # Admin User Management AJAX endpoints
    path('api/create-user/', admin_views.create_user, name='create_user'),
    path('api/get-user/<int:user_id>/', admin_views.get_user, name='get_user'),  # This was missing
    path('api/update-user/', admin_views.update_user, name='update_user'),      # This was missing
    path('api/verify-user/<int:user_id>/', admin_views.verify_user, name='verify_user'),
    path('api/toggle-user-active/<int:user_id>/', admin_views.toggle_user_active, name='toggle_user_active'),
    path('api/bulk-verify-users/', admin_views.bulk_verify_users, name='bulk_verify_users'),
    path('api/export-users/', admin_views.export_users, name='export_users'),
    path('api/user-stats/', admin_views.get_user_stats, name='user_stats'),
    path('api/search-users/', admin_views.search_users, name='search_users'),
]