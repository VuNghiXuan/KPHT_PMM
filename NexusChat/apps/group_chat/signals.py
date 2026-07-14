"""
File: apps/group_chat/signals.py
Mục đích: Lắng nghe tin nhắn mới để kích hoạt AI xử lý (nếu được yêu cầu).
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message
from apps.ai_assistant.services import ai_chat_service

@receiver(post_save, sender=Message)
def trigger_ai_response(sender, instance, created, **kwargs):
    """
    Hàm tự động kích hoạt AI sau khi có tin nhắn mới.
    
    Args:
        instance (Message): Tin nhắn vừa được lưu.
        created (bool): Kiểm tra xem có phải tin nhắn mới không.
    """
    if created and "@AI" in instance.content:
        # Gọi dịch vụ AI để xử lý câu hỏi
        ai_chat_service.generate_response(instance)