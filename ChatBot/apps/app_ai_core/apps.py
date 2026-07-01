from django.apps import AppConfig


class AppAiCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_ai_core'

    # Tên hiển thị trên giao diện Admin cho đẹp
    verbose_name = 'Hệ Thống Quản Lý AI'
