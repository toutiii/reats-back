from django.apps import AppConfig


class CookerAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cooker_app"

    def ready(self):
        import cooker_app.signals
