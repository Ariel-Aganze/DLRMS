# test_gis_imports.py
import os

# CRITICAL: Set GDAL path BEFORE any Django imports
os.environ['GDAL_LIBRARY_PATH'] = r"D:\COURSES\SEM 7\FINAL YEAR PROJECT\CODEBASE\DLRMS\dlrms_project\dlrms_env\Lib\site-packages\osgeo"

print("Testing GIS imports...")

try:
    import django
    print("✅ Django imported successfully")
    
    from django.contrib.gis.db.backends.postgis import base
    print("✅ PostGIS backend imported successfully")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    
try:
    from django.contrib.gis.geos import Point
    print("✅ GEOS (Point) imported successfully")
except ImportError as e:
    print(f"❌ GEOS import error: {e}")

try:
    from django.contrib.gis.gdal import DataSource
    print("✅ GDAL imported successfully")
except ImportError as e:
    print(f"❌ GDAL import error: {e}")

print("\nDone testing imports.")