from django.urls import path
from . import views

app_name = 'disputes'

urlpatterns = [
    path('', views.DisputeListView.as_view(), name='dispute_list'),
    path('create/', views.DisputeCreateView.as_view(), name='dispute_create'),
    path('<int:pk>/', views.DisputeDetailView.as_view(), name='dispute_detail'),
    path('<int:pk>/resolve/', views.DisputeResolveView.as_view(), name='dispute_resolve'),
]