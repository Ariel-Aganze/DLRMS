# Create this file: dlrms_project/certificates/urls.py

from django.urls import path
from . import views
from . import document_views

app_name = 'certificates'

urlpatterns = [
    # Certificate management
    path('', views.CertificateListView.as_view(), name='certificate_list'),
    path('<int:pk>/', views.CertificateDetailView.as_view(), name='certificate_detail'),
    path('generate/<int:application_id>/', views.GenerateCertificateView.as_view(), name='generate_certificate'),
    path('<int:pk>/download/', views.DownloadCertificateView.as_view(), name='download_certificate'),
    path('<int:pk>/sign/', views.SignCertificateView.as_view(), name='sign_certificate'),
    
    # Public verification
    path('verify/', views.VerifyCertificateView.as_view(), name='verify_certificate'),
    path('verify/<uuid:certificate_id>/', views.VerifyCertificateView.as_view(), name='verify_certificate_uuid'),
    
    # Document signing
    path('sign/<str:doc_type>/<int:doc_id>/', document_views.DocumentSigningView.as_view(), name='document_signing'),
    path('sign/ajax/', document_views.sign_document_ajax, name='sign_document_ajax'),
    path('signatures/', document_views.SignedDocumentsListView.as_view(), name='signed_documents'),
    path('signatures/verify/<uuid:signature_id>/', document_views.verify_document_signature, name='verify_signature'),
]