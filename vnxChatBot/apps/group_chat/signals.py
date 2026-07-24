"""
Mục đích: Tự động hóa các tác vụ ngầm thông qua Django Signals.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: group_chat.models, ai_assistant.services, ai_assistant.vector_store
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit
from apps.ai_assistant.services import AIProcessorService

# 1. Quản lý Thành viên nhóm
@receiver(post_save, sender=ChatGroup)
def create_ai_member(sender, instance, created, **kwargs):
    """Khi nhóm mới được tạo, tự động gán AI làm thành viên."""
    if created:
        Membership.objects.create(group=instance, role='member', is_ai=True)

# 2. Quản lý Vòng đời Tài liệu
@receiver(post_save, sender=Document)
def process_document_knowledge(sender, instance, created, **kwargs):
    """Khi có file mới, tạo KnowledgeUnit và kích hoạt xử lý bất đồng bộ."""
    if created:
        unit = KnowledgeUnit.objects.create(
            document=instance,
            group=instance.group,
            entity_name=instance.file.name,
            context_tag="Tự động",
            status='pending'
        )
        # Kích hoạt Celery Task (Import bên trong để tránh circular import)
        from apps.ai_assistant.tasks import process_document_task
        process_document_task.delay(unit.id)

@receiver(post_delete, sender=Document)
def cleanup_vector_store_on_doc_delete(sender, instance, **kwargs):
    """Khi xóa tài liệu, xóa tất cả KnowledgeUnit và embedding liên quan."""
    units = KnowledgeUnit.objects.filter(document=instance)
    for unit in units:
        if unit.status == 'approved':
            AIProcessorService.remove_unit_from_vector(unit.id)
    units.delete()

# 3. Quản lý Vòng đời Tri thức (Feedback Loop)
@receiver(post_save, sender=KnowledgeUnit)
def sync_knowledge_to_vector_db(sender, instance, **kwargs):
    """
    Đồng bộ dữ liệu vào Vector DB dựa trên trạng thái duyệt.
    Mọi logic gọi VectorDBManager đều đi qua AIProcessorService.
    """
    if instance.status == 'approved':
        AIProcessorService.sync_unit_to_vector(instance)
    elif instance.status == 'rollback':
        AIProcessorService.remove_unit_from_vector(instance.id)

