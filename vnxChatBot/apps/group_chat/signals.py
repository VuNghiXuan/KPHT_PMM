# -*- coding: utf-8 -*-
"""
File: apps/group_chat/signals.py
Mục đích: Tự động hóa các tác vụ ngầm thông qua Django Signals cho phân hệ group_chat,
          đảm bảo tuân thủ tuyệt đối quy tắc vòng đời tri thức (Pending -> Staging -> Approved).
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services
"""

import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter
from apps.ai_assistant.services import AIProcessorService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ChatGroup)
def create_ai_member(sender, instance, created, **kwargs):
    """
    🔌 Khi nhóm mới được tạo, tự động khởi tạo thành viên AI đại diện (is_ai=True) 
    phục vụ kiến trúc Group-Centric an toàn với get_or_create.
    """
    if created:
        membership, created_flag = Membership.objects.get_or_create(
            group=instance,
            is_ai=True,
            defaults={'role': 'member'}
        )
        if created_flag:
            logger.info(f"✨ [AI Member Created]: Đã khởi tạo thành viên AI cho nhóm {instance.id}")
        else:
            logger.debug(f"ℹ️ [AI Member Exists]: Thành viên AI đã tồn tại trong nhóm {instance.id}")


@receiver(post_save, sender=KnowledgeChapter)
def handle_knowledge_chapter_sync(sender, instance, created, update_fields=None, **kwargs):
    """
    🧠 Lắng nghe thay đổi trạng thái của KnowledgeChapter để đồng bộ Vector Store:
    - QUY TẮC VÀNG: Chặn tuyệt đối không đưa dữ liệu 'pending' hoặc 'staging' vào VectorDB.
    - Chỉ kích hoạt Celery Task đồng bộ khi và chỉ khi trạng thái chính thức là 'approved'.
    """
    if instance.status != 'approved':
        logger.debug(f"🛡️ [Vector Sync Skipped]: KnowledgeChapter ID {instance.id} đang ở trạng thái '{instance.status}', không đưa vào VectorDB.")
        return

    chapter_id = instance.id
    group_id = str(instance.group_id)
    
    # 🛡️ Dùng transaction.on_commit để đảm bảo DB đã lưu xong dữ liệu approved trước khi Celery Worker chạy
    transaction.on_commit(
        lambda: AIProcessorService.sync_chapter_to_vector_async(group_id, chapter_id)
    )
    logger.info(f"🚀 [Vector Sync Queued]: Đã lên lịch đồng bộ Chapter {chapter_id} vào VectorDB cho nhóm {group_id} (Trạng thái: approved).")


@receiver(post_delete, sender=KnowledgeChapter)
def cleanup_vector_store_on_chapter_delete(sender, instance, **kwargs):
    """
    🗑️ Khi một chương tri thức bị xóa, tự động gỡ bỏ vector embedding tương ứng 
    khỏi Vector Store của nhóm (chỉ thực hiện nếu chương đó trước đó đã được approved).
    """
    chapter_id = instance.id
    group_id = str(instance.group_id)
    
    if instance.status == 'approved':
        transaction.on_commit(
            lambda: AIProcessorService.remove_chapter_from_vector(group_id, chapter_id)
        )
        logger.info(f"🗑️ [Vector Cleanup Queued]: Đã lên lịch gỡ bỏ Approved Chapter {chapter_id} khỏi VectorDB của nhóm {group_id}.")
    else:
        logger.debug(f"🗑️ [Vector Cleanup Skipped]: Chapter {chapter_id} ở trạng thái '{instance.status}' chưa từng được đưa vào VectorDB.")