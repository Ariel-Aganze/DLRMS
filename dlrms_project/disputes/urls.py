# File: dlrms_project/disputes/urls.py

from django.urls import path
from . import views

app_name = 'disputes'

urlpatterns = [
    # Existing URLs
    path('', views.DisputeListView.as_view(), name='dispute_list'),
    path('create/', views.DisputeCreateView.as_view(), name='dispute_create'),
    path('<int:pk>/', views.DisputeDetailView.as_view(), name='dispute_detail'),
    path('<int:pk>/resolve/', views.DisputeResolveView.as_view(), name='dispute_resolve'),
    path('<int:pk>/assign/', views.DisputeAssignView.as_view(), name='dispute_assign'),
    
    # ADD NEW URLs for Dispute Officer functionality
    path('<int:pk>/officer-assign/', views.DisputeOfficerAssignView.as_view(), name='dispute_officer_assign'),
    path('<int:pk>/recommendations/', views.get_approach_recommendations, name='get_approach_recommendations'),
    path('get-template/', views.get_approach_template, name='get_approach_template'),
    path('<int:pk>/guidance-feedback/', views.guidance_feedback, name='guidance_feedback'),

    path('<int:pk>/update-status/', views.update_dispute_status, name='update_dispute_status'),

    
    # Existing AJAX URLs
    path('<int:pk>/add-comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/add-evidence/', views.add_evidence, name='add_evidence'),
    path('<int:pk>/schedule-mediation/', views.schedule_mediation, name='schedule_mediation'),
]