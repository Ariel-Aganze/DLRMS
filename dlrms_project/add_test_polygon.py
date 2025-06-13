from applications.models import ParcelApplication
from land_management.models import ParcelBoundary
from django.contrib.auth import get_user_model
import json

User = get_user_model()

def add_test_polygon(application_id):
    try:
        # Get the application
        application = ParcelApplication.objects.get(id=application_id)
        print(f"Found application: {application}")
        
        # Get an admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            # Try to get a user with admin role
            admin_user = User.objects.filter(role='admin').first()
        if not admin_user:
            # Fall back to any user
            admin_user = User.objects.first()
        
        print(f"Using user: {admin_user}")
        
        # Sample polygon data (simple square around the application coordinates)
        lat = float(application.latitude) if application.latitude else -1.95
        lng = float(application.longitude) if application.longitude else 30.15
        
        polygon_data = [
            [lat - 0.001, lng - 0.001],
            [lat - 0.001, lng + 0.001],
            [lat + 0.001, lng + 0.001],
            [lat + 0.001, lng - 0.001]
        ]
        
        # Calculate area (approximate)
        area_sqm = 111319.9 * 111319.9 * 0.002 * 0.002  # Approximate calculation
        area_hectares = area_sqm / 10000
        
        # Create or update the boundary
        boundary, created = ParcelBoundary.objects.get_or_create(
            application=application,
            defaults={
                'polygon_geojson': json.dumps(polygon_data),
                'center_lat': lat,
                'center_lng': lng,
                'area_sqm': area_sqm,
                'area_hectares': area_hectares,
                'created_by': admin_user
            }
        )
        
        if not created:
            print(f"Updating existing boundary: {boundary.id}")
            boundary.polygon_geojson = json.dumps(polygon_data)
            boundary.center_lat = lat
            boundary.center_lng = lng
            boundary.area_sqm = area_sqm
            boundary.area_hectares = area_hectares
            boundary.updated_by = admin_user
            boundary.save()
            print(f"Boundary updated successfully")
        else:
            print(f"Created new boundary: {boundary.id}")
        
        # Count boundaries in the database
        count = ParcelBoundary.objects.all().count()
        print(f"Total boundaries in database: {count}")
        
        return boundary
    except Exception as e:
        print(f"Error creating test polygon: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Change this to the application ID you want to add a polygon for
application_id = 11
boundary = add_test_polygon(application_id)
print(f"Polygon created/updated: {boundary}")