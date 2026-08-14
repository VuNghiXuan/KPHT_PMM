"""
Mục đích: Tự động hóa các tác vụ ngầm thông qua Django Signals cho phân hệ group_chat.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter
from apps.ai_assistant.services import AIProcessorService

# 1. Quản lý Thành viên nhóm (Giữ nguyên logic ổn định cũ)
@receiver(post_save, sender=ChatGroup)
def create_ai_member(sender, instance, created, **kwargs):
    """Khi nhóm mới được tạo, tự động gán AI làm thành viên (is_ai=True)."""
    if created:
        Membership.objects.create(group=instance, role='member', is_ai=True)

# 2. Quản lý Vòng đời Tri thức & Đồng bộ Vector Store (Nâng cấp lên KnowledgeChapter)
@receiver(post_save, sender=KnowledgeChapter)
def handle_knowledge_chapter_sync(sender, instance, created, **kwargs):
    """
    Lắng nghe sự thay đổi trạng thái của KnowledgeChapter:
    - Nếu mới tạo (pending/staging): Không làm gì cả (Chặn tuyệt đối không đưa vào VectorDB).
    - Nếu trạng thái chuyển thành 'approved': Kích hoạt tiến trình đồng bộ embedding bất đồng bộ.
    """
    if instance.status == 'approved':
        # Sử dụng Celery Task qua AIProcessorService để tách bạch luồng Ghi
        AIProcessorService.sync_chapter_to_vector_async(instance.id)

@receiver(post_delete, sender=KnowledgeChapter)
def cleanup_vector_store_on_chapter_delete(sender, instance, **kwargs):
    """Khi một chương tri thức bị xóa, tiến hành gỡ bỏ vector embedding tương ứng trong Vector Store."""
    if instance.status == 'approved':
        AIProcessorService.remove_chapter_from_vector(instance.id)

@receiver(post_save, sender=KnowledgeChapter)
def handle_knowledge_chapter_sync(sender, instance, created, update_fields, **kwargs):
    """
    Tối ưu hóa: Chỉ đồng bộ nếu trạng thái vừa chuyển sang 'approved' hoặc 
    nội dung 'approved' bị thay đổi.
    """
    # Nếu là bản ghi mới và không phải approved -> Bỏ qua
    if created and instance.status != 'approved':
        return

    # Nếu là bản ghi cũ, chỉ xử lý nếu status là approved
    if instance.status == 'approved':
        AIProcessorService.sync_chapter_to_vector_async(instance.id)