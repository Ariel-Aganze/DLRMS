# test_simple_gdal.py
import os
import django

# Set the exact path before Django imports
os.environ['GDAL_LIBRARY_PATH'] = r"D:\COURSES\SEM 7\FINAL YEAR PROJECT\CODEBASE\DLRMS\dlrms_project\dlrms_env\Lib\site-packages\osgeo"

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dlrms.settings')
django.setup()

try:
    from django.contrib.gis.geos import Point
    print("✅ GEOS Point imported successfully!")
    
    from django.contrib.gis.db.backends.postgis import base
    print("✅ PostGIS backend imported successfully!")
    
    print("🎉 GIS is working!")
    
except Exception as e:
    print(f"❌ Error: {e}")