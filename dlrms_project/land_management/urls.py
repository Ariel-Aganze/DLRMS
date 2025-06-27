from django.urls import path
from . import views

app_name = 'land_management'

urlpatterns = [
    path('parcels/', views.ParcelListView.as_view(), name='parcel_list'),
    path('parcels/create/', views.ParcelCreateView.as_view(), name='parcel_create'),
    path('parcels/<int:pk>/', views.ParcelDetailView.as_view(), name='parcel_detail'),
    path('parcels/<int:pk>/edit/', views.ParcelUpdateView.as_view(), name='parcel_update'),
    path('map/', views.MapView.as_view(), name='map'),

    # Ownership Transfer URLs
    path('my-titles/', views.MyLandTitlesView.as_view(), name='my_titles'),
    path('title/<int:pk>/', views.LandTitleDetailView.as_view(), name='title_detail'),
    path('title/<int:title_pk>/initiate-transfer/', views.InitiateTransferView.as_view(), name='initiate_transfer'),
    path('transfer/<int:pk>/confirm/', views.TransferConfirmationView.as_view(), name='confirm_transfer'),
    path('transfers/', views.TransferListView.as_view(), name='transfer_list'),
    path('transfer/<int:pk>/review/', views.TransferReviewView.as_view(), name='review_transfer'),
    path('transfer/<int:pk>/cancel/', views.cancel_transfer, name='cancel_transfer'),
    path('transfer/<int:pk>/certificate/', views.download_transfer_certificate, name='download_certificate'),
    
    # AJAX endpoints
    path('ajax/check-receiver/', views.check_receiver_details, name='check_receiver'),
]