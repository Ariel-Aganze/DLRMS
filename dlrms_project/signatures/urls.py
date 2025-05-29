from django.urls import path
from . import views

app_name = 'signatures'

urlpatterns = [
    path('', views.SignatureListView.as_view(), name='signature_list'),
    path('sign/<int:pk>/', views.SignDocumentView.as_view(), name='sign_document'),
    path('verify/<uuid:signature_id>/', views.VerifySignatureView.as_view(), name='verify_signature'),
]