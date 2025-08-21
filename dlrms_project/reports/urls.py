from django.urls import path
from . import views
from . import custom_reports

app_name = 'reports'

urlpatterns = [
    path('', views.system_reports_dashboard, name='dashboard'),
    path('audit-logs/', views.audit_logs_list, name='audit_logs'),
    path('certificate-logs/', views.certificate_audit_logs, name='certificate_logs'),
    path('export/audit-logs/', views.export_audit_logs, name='export_audit_logs'),
    path('generate-sample-data/', views.generate_sample_data, name='generate_sample_data'),  

    path('custom-reports/', custom_reports.custom_report_dashboard, name='custom_report_dashboard'),
    path('custom-reports/generate/', custom_reports.generate_custom_report, name='generate_custom_report'),
    path('custom-reports/preview/', custom_reports.preview_report_data, name='preview_report_data'),
]