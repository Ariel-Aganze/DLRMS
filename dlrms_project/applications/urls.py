# applications/urls.py
from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Existing URLs
    path('', views.ApplicationListView.as_view(), name='application_list'),
    path('create/', views.ApplicationCreateView.as_view(), name='application_create'),
    path('<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('<int:pk>/update/', views.ApplicationUpdateView.as_view(), name='application_update'),
    path('<int:pk>/review/', views.ApplicationReviewView.as_view(), name='application_review'),
    
    # New URLs for parcel applications
    path('parcel/', views.ParcelApplicationListView.as_view(), name='parcel_application_list'),
    path('parcel/create/', views.ParcelApplicationCreateView.as_view(), name='parcel_application_create'),
    path('parcel/<int:pk>/', views.ParcelApplicationDetailView.as_view(), name='parcel_application_detail'),
    path('parcel/<int:pk>/assign/', views.AssignFieldAgentView.as_view(), name='assign_field_agent'),
    path('parcel/<int:pk>/review/', views.ReviewApplicationView.as_view(), name='review_application'),
    
    # Parcel title URLs
    path('titles/', views.ParcelTitleListView.as_view(), name='parcel_title_list'),
    path('titles/<int:pk>/', views.ParcelTitleDetailView.as_view(), name='parcel_title_detail'),
]