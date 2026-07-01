from django.apps import AppConfig
from django.db.models.signals import post_migrate

# Thêm *args và **kwargs để hứng hết tham số tự động của Django Signal
def trigger_seed_signal(sender, *args, **kwargs):
    """Signal trung gian để gọi hàm seed từ Service, tránh import gãy luồng"""
    from .models import seed_default_ai_prompt
    
    # Truyền sender (chính là AppConfig) vào hàm theo đúng thiết kế của anh
    seed_default_ai_prompt(sender=sender)

class AppAiCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_ai_core'
    verbose_name = 'Cấu hình AI Core'

    def ready(self):
        # Kết nối vào signal hệ thống
        post_migrate.connect(trigger_seed_signal, sender=self)