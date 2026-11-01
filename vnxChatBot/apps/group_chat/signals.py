# -*- coding: utf-8 -*-
"""
File: apps/group_chat/signals.py
Mục đích: Quản lý các tín hiệu nội bộ của phân hệ group_chat (khởi tạo AI Member).
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.group_chat.models import ChatGroup, Membership

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ChatGroup)
def create_ai_member(sender, instance, created, **kwargs):
    """
    🔌 Khi nhóm mới được tạo, tự động khởi tạo thành viên AI đại diện (is_ai=True).
    Thực thi trực tiếp để đảm bảo hoạt động nhất quán cả trên Production và trong Django TestCase.
    """
    if not created or not instance.pk:
        return

    try:
        membership, created_flag = Membership.objects.get_or_create(
            group=instance,
            is_ai=True,
            user=None,  
            defaults={'role': 'member'}
        )
        if created_flag:
            logger.info(f"✨ [AI Member Created]: Đã khởi tạo thành viên AI cho nhóm {instance.id}")
    except Exception as e:
        logger.error(f"❌ [Signals] Lỗi khởi tạo thành viên AI cho nhóm {instance.id}: {str(e)}")