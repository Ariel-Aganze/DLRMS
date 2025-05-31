# test_postgis_complete.py
# Place this file in your dlrms_project directory (same level as manage.py)

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))

# Set up environment variables BEFORE Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dlrms.settings')

def test_gdal_geos_libraries():
    """Test GDAL and GEOS library loading"""
    print("=" * 60)
    print("TESTING GDAL/GEOS LIBRARIES")
    print("=" * 60)
    
    try:
        # Test GDAL
        from osgeo import gdal
        print(f"✅ GDAL imported successfully - Version: {gdal.VersionInfo()}")
        
        # Test GEOS
        from osgeo import ogr
        print("✅ OGR (part of GDAL) imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ GDAL/GEOS import failed: {e}")
        return False

def test_django_gis_imports():
    """Test Django GIS imports"""
    print("\n" + "=" * 60)
    print("TESTING DJANGO GIS IMPORTS")
    print("=" * 60)
    
    try:
        # Setup Django
        django.setup()
        print("✅ Django setup successful")
        
        # Test GEOS
        from django.contrib.gis.geos import Point, Polygon
        print("✅ Django GEOS (Point, Polygon) imported successfully")
        
        # Test GDAL
        from django.contrib.gis.gdal import DataSource
        print("✅ Django GDAL imported successfully")
        
        # Test PostGIS backend
        from django.contrib.gis.db.backends.postgis import base
        print("✅ PostGIS backend imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Django GIS import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection and PostGIS functionality"""
    print("\n" + "=" * 60)
    print("TESTING DATABASE CONNECTION")
    print("=" * 60)
    
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Test basic connection
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ PostgreSQL connected - Version: {version[0][:50]}...")
            
            # Test PostGIS
            cursor.execute("SELECT PostGIS_version();")
            postgis_version = cursor.fetchone()
            print(f"✅ PostGIS Version: {postgis_version[0]}")
            
            # Test PostGIS extensions
            cursor.execute("""
                SELECT name, default_version, installed_version 
                FROM pg_available_extensions 
                WHERE name LIKE 'postgis%' AND installed_version IS NOT NULL;
            """)
            extensions = cursor.fetchall()
            print("✅ Installed PostGIS Extensions:")
            for ext in extensions:
                print(f"   - {ext[0]}: {ext[2]}")
            
            # Test spatial query
            cursor.execute("SELECT ST_Point(30.0619, -1.9441);")  # North Kivu coordinates
            point_result = cursor.fetchone()
            print(f"✅ Spatial query successful: {str(point_result[0])[:50]}...")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_django_gis_functionality():
    """Test Django GIS model functionality"""
    print("\n" + "=" * 60)
    print("TESTING DJANGO GIS FUNCTIONALITY")
    print("=" * 60)
    
    try:
        from django.contrib.gis.geos import Point
        
        # Create a test point
        test_point = Point(30.0619, -1.9441, srid=4326)  # North Kivu coordinates
        print(f"✅ Point created: {test_point}")
        print(f"   - Latitude: {test_point.y}")
        print(f"   - Longitude: {test_point.x}")
        print(f"   - SRID: {test_point.srid}")
        
        # Test coordinate transformations
        test_point_3857 = test_point.transform(3857, clone=True)
        print(f"✅ Coordinate transformation successful (EPSG:3857)")
        
        return True
        
    except Exception as e:
        print(f"❌ Django GIS functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_land_parcel_model():
    """Test the LandParcel model with GIS fields"""
    print("\n" + "=" * 60)
    print("TESTING LAND PARCEL MODEL")
    print("=" * 60)
    
    try:
        from land_management.models import LandParcel
        from django.contrib.gis.geos import Point
        from accounts.models import User
        
        # Check if we can access the model
        print("✅ LandParcel model imported successfully")
        
        # Test model structure
        field_names = [f.name for f in LandParcel._meta.get_fields()]
        print(f"✅ Model fields: {', '.join(field_names)}")
        
        # Check for GIS fields
        gis_fields = [f for f in LandParcel._meta.get_fields() 
                     if hasattr(f, 'geom_type')]
        print(f"✅ GIS fields found: {[f.name for f in gis_fields]}")
        
        return True
        
    except Exception as e:
        print(f"❌ LandParcel model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_migrations_check():
    """Check if migrations are needed"""
    print("\n" + "=" * 60)
    print("CHECKING MIGRATIONS")
    print("=" * 60)
    
    try:
        from django.core.management import execute_from_command_line
        
        print("🔍 Checking for unapplied migrations...")
        
        # This will show which migrations need to be applied
        result = os.system('python manage.py showmigrations --plan')
        
        print("\n💡 If you see unapplied migrations above, run:")
        print("   python manage.py makemigrations")
        print("   python manage.py migrate")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 DLRMS PostGIS Configuration Test")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run all tests
    tests = [
        test_gdal_geos_libraries,
        test_django_gis_imports,
        test_database_connection,
        test_django_gis_functionality,
        test_land_parcel_model,
        run_migrations_check
    ]
    
    for test in tests:
        try:
            result = test()
            if not result:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            all_tests_passed = False
    
    # Final result
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! PostGIS is properly configured.")
        print("✅ You can now run: python manage.py makemigrations")
        print("✅ Then run: python manage.py migrate")
        print("✅ Your DLRMS project is ready for GIS functionality!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("💡 Common solutions:")
        print("   1. Ensure PostgreSQL is running")
        print("   2. Check your database credentials in .env")
        print("   3. Make sure PostGIS extensions are installed")
        print("   4. Verify GDAL/GEOS library paths")
    print("=" * 60)

if __name__ == "__main__":
    main()