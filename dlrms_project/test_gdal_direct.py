# test_gdal_direct.py
import os
import ctypes

# Set the exact DLL path
gdal_dll_path = r"D:\COURSES\SEM 7\FINAL YEAR PROJECT\CODEBASE\DLRMS\dlrms_project\dlrms_env\Lib\site-packages\osgeo\gdal.dll"

print(f"Testing direct GDAL DLL loading: {gdal_dll_path}")
print(f"DLL exists: {os.path.exists(gdal_dll_path)}")

# Try to load the DLL directly
try:
    gdal_lib = ctypes.CDLL(gdal_dll_path)
    print("✅ GDAL DLL loaded successfully with ctypes")
except Exception as e:
    print(f"❌ Failed to load GDAL DLL: {e}")

# Set environment variables for Django
os.environ['GDAL_LIBRARY_PATH'] = gdal_dll_path  # Point to the exact file
os.environ['GDAL_DATA'] = os.path.dirname(gdal_dll_path)

# Also try setting the directory
os.environ['GDAL_DIR'] = os.path.dirname(gdal_dll_path)

print("Environment variables set:")
print(f"GDAL_LIBRARY_PATH: {os.environ.get('GDAL_LIBRARY_PATH')}")
print(f"GDAL_DATA: {os.environ.get('GDAL_DATA')}")

# Now try Django imports
try:
    import django
    print("✅ Django imported")
    
    from django.contrib.gis.gdal.libgdal import lgdal
    print("✅ Django GDAL library loaded successfully!")
    
    from django.contrib.gis.geos import Point
    print("✅ GEOS Point imported successfully!")
    
    from django.contrib.gis.db.backends.postgis import base
    print("✅ PostGIS backend imported successfully!")
    
    print("\n🎉 All GIS components working!")
    
except Exception as e:
    print(f"❌ Django GIS import failed: {e}")
    import traceback
    traceback.print_exc()