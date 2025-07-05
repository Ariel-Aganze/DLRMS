# dlrms_project/dlrms/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # This handles all core URLs including API endpoints
    path('accounts/', include('accounts.urls')),
    path('land/', include('land_management.urls')),
    path('applications/', include('applications.urls')),
    path('documents/', include('documents.urls')),
    path('notifications/', include('notifications.urls')),
    path('disputes/', include('disputes.urls')),
    path('signatures/', include('signatures.urls')),
    path('certificates/', include('certificates.urls')),
    path('reports/', include('reports.urls', namespace='reports')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()

# Admin site customization
admin.site.site_header = "DLRMS Administration"
admin.site.site_title = "DLRMS Admin Portal"
admin.site.index_title = "Welcome to DLRMS Administration"