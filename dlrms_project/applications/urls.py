# applications/urls.py
from django.urls import include, path

from . import reviewviews
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

    path('review/', include([
        path('dashboard/', 
             reviewviews.ApplicationsReviewDashboardView.as_view(), 
             name='review_dashboard'),
        path('api/applications/', 
             reviewviews.applications_api_list, 
             name='api_applications_list'),
        path('api/applications/<int:application_id>/quick-review/', 
             reviewviews.quick_application_review, 
             name='api_quick_review'),
        path('api/applications/<int:application_id>/comments/', 
             reviewviews.application_comments, 
             name='api_application_comments'),
        path('api/applications/bulk-assign/', 
             reviewviews.assign_field_agent_bulk, 
             name='api_bulk_assign'),
        path('api/applications/change-priority/', 
             reviewviews.change_application_priority, 
             name='api_change_priority'),
        path('api/applications/export/', 
             reviewviews.export_applications, 
             name='api_export_applications'),
        path('api/applications/analytics/', 
             reviewviews.application_analytics, 
             name='api_analytics'),
        path('api/workload-distribution/', 
             reviewviews.applications_workload_distribution, 
             name='api_workload_distribution'),
        path('<int:pk>/detailed-review/', 
             reviewviews.ApplicationDetailReviewView.as_view(), 
             name='detailed_review'),
        path('reports/', 
             reviewviews.ApplicationsReportView.as_view(), 
             name='reports'),
    ])),

]