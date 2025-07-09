# File: applications/urls.py (Updated with API endpoints for inspection modal)
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
    
    # Surveyor specific URLs
    path('inspections/', views.SurveyorInspectionsView.as_view(), name='surveyor_inspections'),
    path('parcel/<int:application_id>/complete-inspection/', views.complete_field_inspection, name='complete_field_inspection'),
    
    # API Endpoints for inspection modal
    path('api/inspection/<int:application_id>/', views.get_inspection_details, name='api_inspection_details'),
    path('api/completed-inspection/<int:application_id>/', views.get_completed_inspection_details, name='api_completed_inspection_details'),
    
    # Polygon API endpoints (removed duplicates)
    path('api/save-polygon/<int:application_id>/', views.save_polygon_data, name='api_save_polygon'),
    path('api/get-polygon/<int:application_id>/', views.get_polygon_data, name='api_get_polygon'),
    
    # Field inspection view
    path('inspection/<int:pk>/', views.FieldInspectionView.as_view(), name='field_inspection'),
    
    # Enhanced parcel application detail view
    path('parcel/<int:pk>/enhanced/', views.EnhancedParcelApplicationDetailView.as_view(), name='parcel_application_detail_enhanced'),
    # Proprerty boundary view
    path('parcel/<int:pk>/boundary-map/', views.PropertyBoundaryMapView.as_view(), name='property_boundary_map'),

    # Add this to your urls.py for debugging
    path('api/test-polygon/<int:application_id>/', views.test_polygon_data, name='test_polygon_data'),

    path('api/direct-test/<int:application_id>/', views.direct_polygon_test, name='direct_polygon_test'),

    # Review Dashboard URLs
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
        path('api/applications/<int:application_id>/registry-approval/', 
             reviewviews.registry_approval, 
             name='api_registry_approval'),
        path('api/applications/export/', 
             reviewviews.export_applications, 
             name='api_export_applications'),
    ])),
]