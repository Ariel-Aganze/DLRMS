from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.system_reports_dashboard, name='dashboard'),
    path('audit-logs/', views.audit_logs_list, name='audit_logs'),
    path('certificate-logs/', views.certificate_audit_logs, name='certificate_logs'),
    path('export/audit-logs/', views.export_audit_logs, name='export_audit_logs'),
    path('generate-sample-data/', views.generate_sample_data, name='generate_sample_data'),  # Add this line
]