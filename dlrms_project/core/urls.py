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
    path('admin/verify-user/<int:user_id>/', admin_views.verify_user, name='verify_user'),
    path('admin/toggle-user-active/<int:user_id>/', admin_views.toggle_user_active, name='toggle_user_active'),
    path('admin/bulk-verify-users/', admin_views.bulk_verify_users, name='bulk_verify_users'),
    path('admin/export-users/', admin_views.export_users, name='export_users'),
    path('admin/user-stats/', admin_views.get_user_stats, name='user_stats'),
    path('admin/search-users/', admin_views.search_users, name='search_users'),
]