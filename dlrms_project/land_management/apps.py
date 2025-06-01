from django.apps import AppConfig

class LandManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'land_management'
    verbose_name = 'Land Management'
    
    def ready(self):
        # Import signals if you have any
        try:
            import land_management.signals
        except ImportError:
            pass