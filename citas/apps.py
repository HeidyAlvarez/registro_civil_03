from django.apps import AppConfig

class CitasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'citas'

    def ready(self):
        # Esto le dice a Django: "Activa los sensores de auditoría ahora mismo"
        import citas.signals