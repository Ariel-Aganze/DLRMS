# PostGIS Setup Notes

## Current Status
- Using SQLite temporarily for development
- PostGIS/GDAL installation pending

## To Enable PostGIS Later:

1. Install OSGeo4W with GDAL/GEOS/PROJ
2. Or use conda environment with spatial packages
3. Uncomment GIS-related settings in settings.py
4. Add 'django.contrib.gis' to INSTALLED_APPS
5. Add 'leaflet' to INSTALLED_APPS  
6. Switch database engine to 'django.contrib.gis.db.backends.postgis'
7. Run migrations with PostGIS

## Commands for later:
```bash
# When PostGIS is ready
python manage.py makemigrations
python manage.py migrate