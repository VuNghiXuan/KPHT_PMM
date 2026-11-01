from django.apps import AppConfig

class AppKnowledgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_knowledge'
    
    # Đặt là số 3 để nó đứng sau app Coach
    verbose_name = '3. Trung tâm Tri thức (Knowledge)'