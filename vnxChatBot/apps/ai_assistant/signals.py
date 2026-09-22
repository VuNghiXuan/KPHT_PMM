# -*- coding: utf-8 -*-
# Path: apps/ai_assistant/signals.py
# Description: Kết nối sự kiện Vòng đời tri thức và Tự động khởi tạo nhóm cho User mới.

import logging
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.ai_assistant.tasks import sync_chapter_to_vector_async
from apps.group_chat.models import ChatGroup, Document, KnowledgeChapter, Membership
from apps.ai_assistant.models.text_choices import KnowledgeStatus
from apps.ai_assistant.vector_store import VectorDBManager

logger = logging.getLogger(__name__)


# --- SIGNALS CHO DOCUMENT ---

@receiver(post_delete, sender=Document)
def handle_document_cleanup(sender, instance, **kwargs):
    """Xóa file vật lý hoặc log liên quan khi Document bị gỡ bỏ."""
    try:
        logger.info(f"🗑️ [Signals] Document ID: {instance.id} đã bị xóa khỏi hệ thống.")
    except Exception as e:
        logger.exception(f"❌ [Signals] Lỗi xử lý dọn dẹp Document {instance.id}")


# --- SIGNALS CHO KNOWLEDGE CHAPTER ---

@receiver(post_save, sender=KnowledgeChapter)
def handle_knowledge_chapter_lifecycle(sender, instance, created, **kwargs):
    """
    Quản lý vòng đời KnowledgeChapter:
    - Khi tạo mới (created=True): Ghi log trạng thái và KHÔNG kích hoạt Celery Task.
    - Khi cập nhật:
      + Nếu status == 'approved': Gọi task bất đồng bộ đẩy vào VectorDB.
      + Nếu status != 'approved': Bỏ qua hoặc chỉ gỡ nếu cần thiết.
    """
    if created:
        logger.info(
            f"⏳ [Knowledge Lifecycle] Chương tri thức mới #{instance.id} "
            f"được khởi tạo ở trạng thái '{instance.status}' (Group: {instance.group_id})"
        )
        return

    # Quy tắc Vàng: Chỉ trạng thái 'approved' mới kích hoạt đồng bộ vào Vector Store
    if instance.status == KnowledgeStatus.APPROVED:
        logger.info(f"🚀 [Vector Sync Triggered]: Chapter ID {instance.id} đã được phê duyệt. Đang gửi task đồng bộ...")
        sync_chapter_to_vector_async.delay(
            str(instance.group_id),
            instance.id
        )
    else:
        logger.info(f"🛡️ [Vector Store Guarded]: Chapter ID {instance.id} ở trạng thái '{instance.status}'. Bỏ qua đồng bộ Vector Store.")


@receiver(post_delete, sender=KnowledgeChapter)
def handle_knowledge_chapter_delete(sender, instance, **kwargs):
    """Gỡ bỏ embedding khỏi VectorDB khi KnowledgeChapter bị xóa khỏi CSDL."""
    try:
        logger.info(f"🗑️ [Vector Cleanup]: Đang xóa Vector DB cho Chapter ID {instance.id} (Group: {instance.group_id})")
        VectorDBManager.delete_unit_embeddings(unit_id=instance.id, group_id=instance.group_id)
    except Exception as e:
        logger.error(f"❌ [Vector Cleanup Error]: Không thể xóa Vector embedding cho Chapter {instance.id}: {str(e)}")


# --- SIGNALS CHO USER ONBOARDING ---

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_chat_group_for_new_user(sender, instance, created, **kwargs):
    """Tự động khởi tạo không gian làm việc nhóm riêng cho User mới đăng ký."""
    if not created:
        return

    def _create_group_and_membership():
        try:
            with transaction.atomic():
                group = ChatGroup.objects.create(
                    name=f"Nhóm làm việc của {instance.username}", 
                    ai_provider="gemini"
                )
                
                Membership.objects.create(
                    user=instance, 
                    group=group, 
                    role="admin"
                )
                
                logger.info(
                    f"👥 [Signals] Đã khởi tạo nhóm mặc định thành công cho User: {instance.username} (ID: {instance.pk})"
                )
        except Exception:
            logger.exception(
                f"❌ [Signals] Lỗi khởi tạo nhóm cho User ID {instance.pk}"
            )

    transaction.on_commit(_create_group_and_membership)