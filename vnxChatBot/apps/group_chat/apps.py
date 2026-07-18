# apps/group_chat/apps.py
"""
Mục đích: Cấu hình App group_chat và đăng ký Signals.
Tác giả: Kiến trúc sư vnxChatBot
"""
from django.apps import AppConfig

class GroupChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.group_chat'
    verbose_name = 'Quản lý Nhóm Chat'

    def ready(self):
        """
        Phương thức này chạy khi dự án khởi động.
        Chúng ta import signals ở đây để đăng ký chúng vào hệ thống.
        """
        import apps.group_chat.signals  # Đảm bảo Signal được nạp
        import apps.ai_assistant.signals # Đảm bảo Signal AI được nạp