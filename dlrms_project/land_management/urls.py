from django.urls import path
from . import views

app_name = 'land_management'

urlpatterns = [
    # Dashboard URLs
    path('dashboard/', views.LandOwnerDashboardView.as_view(), name='dashboard'),
    path('registrar/dashboard/', views.RegistrarDashboardView.as_view(), name='registrar_dashboard'),
    
    # Parcel URLs
    path('parcels/', views.ParcelListView.as_view(), name='parcel_list'),
    path('parcels/<int:pk>/', views.ParcelDetailView.as_view(), name='parcel_detail'),
    
    # Application URLs
    path('applications/', views.ApplicationListView.as_view(), name='application_list'),
    path('applications/create/', views.ParcelApplicationCreateView.as_view(), name='application_create'),
    path('applications/<int:pk>/', views.ParcelApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:pk>/review/', views.ApplicationReviewView.as_view(), name='application_review'),
    
    # Map and AJAX URLs
    path('map/', views.MapView.as_view(), name='map'),
    path('api/parcel/<int:parcel_id>/', views.get_parcel_details, name='parcel_details_api'),
]