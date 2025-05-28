from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.ApplicationListView.as_view(), name='application_list'),
    path('create/', views.ApplicationCreateView.as_view(), name='application_create'),
    path('<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('<int:pk>/update/', views.ApplicationUpdateView.as_view(), name='application_update'),
    path('<int:pk>/review/', views.ApplicationReviewView.as_view(), name='application_review'),
]