import os
import sys
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# CRITICAL: GDAL Configuration for Windows
if os.name == 'nt':  # Windows
    # Get the virtual environment path dynamically
    venv_path = os.path.dirname(sys.executable)
    if 'dlrms_env' in venv_path:
        # We're in the virtual environment
        osgeo_path = os.path.join(os.path.dirname(venv_path), 'Lib', 'site-packages', 'osgeo')
    else:
        # Fallback to your specific path
        osgeo_path = r"D:\COURSES\SEM 7\FINAL YEAR PROJECT\CODEBASE\DLRMS\dlrms_project\dlrms_env\Lib\site-packages\osgeo"
    
    # Set environment variables BEFORE any Django GIS imports
    os.environ['GDAL_LIBRARY_PATH'] = osgeo_path
    os.environ['GEOS_LIBRARY_PATH'] = osgeo_path
    os.environ['GDAL_DATA'] = osgeo_path
    os.environ['PROJ_LIB'] = osgeo_path  # This fixes the proj.db error
    
    # Set specific library paths
    GDAL_LIBRARY_PATH = os.path.join(osgeo_path, 'gdal.dll')
    GEOS_LIBRARY_PATH = os.path.join(osgeo_path, 'geos_c.dll')
    
    print(f"✅ GDAL configured at: {GDAL_LIBRARY_PATH}")
    print(f"✅ GEOS configured at: {GEOS_LIBRARY_PATH}")
    print(f"✅ PROJ_LIB set to: {osgeo_path}")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # Enable GIS support
    
    # Third party apps
    'leaflet',  # Enable Leaflet for maps
    'crispy_forms',
    'crispy_tailwind',
    'django_extensions',
    'import_export',
    
    # Local apps
    'core',
    'accounts',
    'land_management',
    'applications',
    'documents',
    'notifications',
    'disputes',
    'signatures',
     'certificates',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dlrms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dlrms.wsgi.application'

# Database - PostgreSQL with PostGIS (FIXED - removed invalid init_command)
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME', default='dlrms_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='arikuagz'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kigali'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# Leaflet Configuration for North Kivu, DRC
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (-1.9441, 30.0619),  # North Kivu coordinates
    'DEFAULT_ZOOM': 10,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
    'ATTRIBUTION_PREFIX': 'DLRMS - North Kivu Land Management',
    'TILES': [
        ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            'attribution': '© OpenStreetMap contributors'
        }),
        ('Satellite', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            'attribution': 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        }),
    ],
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Use SMTP backend
# For development, you can use console backend:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Production email settings (example with Gmail)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'appdevmailfortesting@gmail.com'  # Your email
EMAIL_HOST_PASSWORD = 'lyxs qnlg ougd ksoa'  # Your app password

# Default email settings
DEFAULT_FROM_EMAIL = 'DLRMS System <noreply@dlrms.gov.cd>'
SERVER_EMAIL = 'DLRMS Server <server@dlrms.gov.cd>'

# Site URL for email links
SITE_URL = 'http://192.168.1.68:8000'  # To change to the actual domain

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Session Settings
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

CSRF_TRUSTED_ORIGINS = [
    'https://yourdomain.com',
    'https://76a3-2c0f-eb68-64d-8500-d9cb-9ee3-aa12-f2f1.ngrok-free.app',  
    # Add other trusted origins if needed
]

CERTIFICATE_VERIFICATION_BASE_URL = 'http://192.168.1.81:8000/certificates'