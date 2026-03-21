from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Start background agents if enabled
        # Ensure it only runs once in runserver (reloader child)
        import os
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('DJANGO_SETTINGS_MODULE'):
            from .agent_manager import start_agents
            start_agents()
