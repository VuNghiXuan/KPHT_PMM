"""
Mục đích: Tự động khởi tạo gói dịch vụ cho nhóm mới.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.group_chat.models import ChatGroup
from .models import Subscription

@receiver(post_save, sender=ChatGroup)
def create_default_subscription(sender, instance, created, **kwargs):
    """
    Khi ChatGroup mới được tạo, tự động tạo gói 'free' cho nhóm đó.
    """
    if created:
        Subscription.objects.create(
            group=instance,
            plan_type='free',
            member_limit=6,  # Giới hạn 6 thành viên bao gồm AI
            is_active=True
        )