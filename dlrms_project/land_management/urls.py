from django.urls import path
from . import views

app_name = 'land_management'

urlpatterns = [
    path('parcels/', views.ParcelListView.as_view(), name='parcel_list'),
    path('parcels/create/', views.ParcelCreateView.as_view(), name='parcel_create'),
    path('parcels/<int:pk>/', views.ParcelDetailView.as_view(), name='parcel_detail'),
    path('parcels/<int:pk>/edit/', views.ParcelUpdateView.as_view(), name='parcel_update'),
    path('map/', views.MapView.as_view(), name='map'),
]