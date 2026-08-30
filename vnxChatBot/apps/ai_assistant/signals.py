"""
Module: ai_assistant.signals
Author: Kỹ sư Phần mềm Cao cấp / Kiến trúc trưởng VnxChatBot
Description: Kết nối sự kiện Vòng đời tri thức (KnowledgeChapter status: pending -> approved) 
             với VectorDB theo chuẩn Group-Centric.
             Tối ưu hóa: Loại bỏ hoàn toànindexing tự động bừa bãi ở Document, tuân thủ tuyệt đối 
             quy trình kiểm duyệt chương mục trước khi đẩy vào RAG.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import logging

from apps.group_chat.models import Document, ChatGroup, Membership, KnowledgeChapter
from apps.ai_assistant.services.document_processor import DocumentProcessorService
from apps.ai_assistant.vector_store import VectorDBManager

logger = logging.getLogger(__name__)

# --- SIGNALS CHO DOCUMENT (Chỉ theo dõi quản lý tệp gốc, KHÔNG tự động index vào VectorDB) ---

@receiver(post_delete, sender=Document)
def handle_document_cleanup(sender, instance, **kwargs):
    """Xóa file vật lý hoặc log liên quan khi Document bị gỡ bỏ."""
    try:
        logger.info(f"🗑️ [Signals] Document ID: {instance.id} đã bị xóa khỏi hệ thống.")
    except Exception as e:
        logger.error(f"❌ [Signals] Lỗi xử lý dọn dẹp Document {instance.id}: {str(e)}")


# --- SIGNALS CHO KNOWLEDGE CHAPTER (Vòng đời tri thức chuẩn RAG theo chương mục nhóm) ---

@receiver(post_save, sender=KnowledgeChapter)
def handle_knowledge_chapter_lifecycle(sender, instance, created, **kwargs):
    """
    Lắng nghe sự thay đổi trạng thái của KnowledgeChapter.
    - Nếu tạo mới: Giữ nguyên trạng thái chờ duyệt (pending) hoặc staging.
    - Nếu status chuyển thành 'approved': Tự động gọi Service đưa dữ liệu chương vào VectorDB theo group_id.
    - Tuân thủ Quy tắc Vàng: Dữ liệu pending/staging cấm tuyệt đối không đẩy vào Vector Store.
    """
    if created:
        logger.info(f"⏳ [Knowledge Lifecycle] Chương tri thức mới #{instance.id} được khởi tạo ở trạng thái '{instance.status}' (Group: {instance.group_id})")
        return

    # Kiểm tra nếu KnowledgeChapter vừa chuyển sang trạng thái phê duyệt (approved)
    if instance.status == 'approved':
        try:
            # Gọi service commit chương tri thức vào VectorDB theo chuẩn group_id
            success = DocumentProcessorService.commit_chapter_to_vector_db(instance)
            if success:
                # Cập nhật mốc thời gian duyệt (approved_at) nếu chưa có mà không kích hoạt signal lặp vòng
                if not instance.approved_at:
                    KnowledgeChapter.objects.filter(pk=instance.pk).update(approved_at=timezone.now())
                logger.info(f"✅ [Signals] Đã đồng bộ thành công KnowledgeChapter #{instance.id} vào VectorDB.")
            else:
                logger.warning(f"⚠️ [Signals] Đồng bộ VectorDB không thành công cho KnowledgeChapter #{instance.id}.")
        except Exception as e:
            logger.error(f"❌ [Signals] Lỗi xử lý commit VectorDB cho KnowledgeChapter #{instance.id}: {str(e)}")


@receiver(post_delete, sender=KnowledgeChapter)
def handle_knowledge_chapter_cleanup(sender, instance, **kwargs):
    """Xóa các embedding tương ứng trong VectorDB trước khi KnowledgeChapter bị xóa vĩnh viễn."""
    try:
        vector_manager = VectorDBManager(group_id=instance.group_id)
        vector_manager.delete_chapter_embeddings(chapter_id=instance.id)
        logger.info(f"🗑️ [Signals] Đã dọn dẹp toàn bộ vector của KnowledgeChapter #{instance.id} (Group ID: {instance.group_id})")
    except Exception as e:
        logger.error(f"❌ [Signals] Lỗi khi dọn dẹp vector cho KnowledgeChapter #{instance.id}: {str(e)}")


# --- SIGNALS CHO USER ONBOARDING ---
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_chat_group_for_new_user(sender, instance, created, **kwargs):
    """Tự động khởi tạo không gian làm việc nhóm riêng cho User mới đăng ký."""
    if created:
        try:
            # Bổ sung ai_provider mặc định để thỏa mãn ràng buộc NOT NULL của cơ sở dữ liệu
            group = ChatGroup.objects.create(
                name=f"Nhóm làm việc của {instance.username}",
                ai_provider='gemini'
            )
            Membership.objects.create(user=instance, group=group, role='admin')
            logger.info(f"👥 [Signals] Đã khởi tạo nhóm mặc định cho User: {instance.username}")
        except Exception as e:
            logger.error(f"❌ [Signals] Lỗi khởi tạo nhóm cho User {instance.username}: {str(e)}")