from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "auth"
    label = "nylo_auth"
    verbose_name = "Nylo Auth"

    def ready(self):
        from django.db.models.signals import post_migrate

        from auth.bootstrap import safe_sync_default_permissions

        post_migrate.connect(safe_sync_default_permissions, sender=self)
        safe_sync_default_permissions()
