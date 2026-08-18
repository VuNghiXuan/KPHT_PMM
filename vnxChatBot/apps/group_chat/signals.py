"""
File: apps/group_chat/signals.py
Mục đích: Tự động hóa các tác vụ ngầm thông qua Django Signals cho phân hệ group_chat,
         đảm bảo tuân thủ tuyệt đối quy tắc vòng đời tri thức (Pending -> Staging -> Approved).
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter
from apps.ai_assistant.services import AIProcessorService

@receiver(post_save, sender=ChatGroup)
def create_ai_member(sender, instance, created, **kwargs):
    """
    🔌 Khi nhóm mới được tạo, tự động khởi tạo thành viên AI đại diện (is_ai=True) 
    phục vụ kiến trúc Group-Centric.
    """
    if created:
        Membership.objects.create(group=instance, role='member', is_ai=True)


@receiver(post_save, sender=KnowledgeChapter)
def handle_knowledge_chapter_sync(sender, instance, created, update_fields=None, **kwargs):
    """
    🧠 Lắng nghe thay đổi trạng thái của KnowledgeChapter để đồng bộ Vector Store:
    - Chặn tuyệt đối không đưa dữ liệu 'pending' hoặc 'staging' vào VectorDB.
    - Chỉ kích hoạt Celery Task đồng bộ khi trạng thái là 'approved'.
    """
    # 1. Nếu là bản ghi mới tạo mà chưa được duyệt -> Bỏ qua
    if created and instance.status != 'approved':
        return

    # 2. Nếu có cập nhật trường, kiểm tra xem có cần thiết phải đồng bộ lại không
    if update_fields and 'status' in update_fields and instance.status != 'approved':
        return

    # 3. Nếu trạng thái là approved, đẩy tác vụ đồng bộ sang Celery Worker (Luồng Ghi bất đồng bộ)
    if instance.status == 'approved':
        AIProcessorService.sync_chapter_to_vector_async(str(instance.group_id), instance.id)


@receiver(post_delete, sender=KnowledgeChapter)
def cleanup_vector_store_on_chapter_delete(sender, instance, **kwargs):
    """
    🗑️ Khi một chương tri thức bị xóa, tự động gỡ bỏ vector embedding tương ứng 
    khỏi Vector Store của nhóm.
    """
    if instance.status == 'approved':
        AIProcessorService.remove_chapter_from_vector(str(instance.group_id), instance.id)