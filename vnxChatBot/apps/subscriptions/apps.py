from django.apps import AppConfig

class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.subscriptions'
    verbose_name = 'Quản lý Gói dịch vụ'

    def ready(self):
        import apps.subscriptions.signals # Kích hoạt signal