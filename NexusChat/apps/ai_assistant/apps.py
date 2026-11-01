"""
File: apps/ai_assistant/apps.py
"""
from django.apps import AppConfig

class AiAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_assistant'
    verbose_name = '02. Trợ lý AI'

    def ready(self):
        import apps.ai_assistant.signals  # Import signals để kích hoạt