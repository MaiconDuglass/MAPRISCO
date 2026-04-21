from django.apps import AppConfig


class MonitoramentoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.monitoramento'

    def ready(self):
        import apps.monitoramento.signals  # Conecta os signals