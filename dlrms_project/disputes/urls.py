from django.urls import path
from . import views

app_name = 'disputes'

urlpatterns = [
    # Main views
    path('', views.DisputeListView.as_view(), name='dispute_list'),
    path('create/', views.DisputeCreateView.as_view(), name='dispute_create'),
    path('<int:pk>/', views.DisputeDetailView.as_view(), name='dispute_detail'),
    path('<int:pk>/resolve/', views.DisputeResolveView.as_view(), name='dispute_resolve'),
    path('<int:pk>/assign/', views.DisputeAssignView.as_view(), name='dispute_assign'),
    
    # AJAX endpoints
    path('<int:pk>/add-comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/add-evidence/', views.add_evidence, name='add_evidence'),
]