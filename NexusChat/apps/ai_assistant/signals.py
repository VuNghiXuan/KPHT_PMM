"""
File: apps/ai_assistant/signals.py
Mục đích: Kết nối sự kiện Model (Upload/Delete) với logic AI & VectorDB.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Document
from .file_processor import extract_text_from_file
# from .vector_store import vector_service # Bây giờ đã import được nhờ __init__.py
from .vector_store.chromadb_client import db_client as vector_service
from apps.group_chat.models import ChatGroup, Membership

@receiver(post_save, sender=Document)
def process_document_to_vector(sender, instance, created, **kwargs):
    """
    Tự động hóa: File được upload -> Trích xuất Text -> Nạp vào VectorDB
    """
    if created and instance.file:
        file_path = instance.file.path
        text_content = extract_text_from_file(file_path)
        
        if text_content:
            # Lưu ý: Hàm của bạn đã đổi tên thành .insert()
            vector_service.insert(
                group_id=instance.group.id,
                text=text_content,
                doc_id=instance.id
            )
            
            # Cập nhật thời gian xử lý
            from django.utils import timezone
            instance.processed_at = timezone.now()
            instance.save(update_fields=['processed_at'])
            
            print(f"✅ Đã nạp tri thức vào VectorDB từ file: {instance.file.name}")

@receiver(post_delete, sender=Document)
def remove_document_from_vector(sender, instance, **kwargs):
    """
    Dọn dẹp: Khi file bị xóa trong Django, xóa luôn vector trong ChromaDB
    """
    vector_service.delete_document(doc_id=instance.id)
    print(f"🗑️ Đã xóa tri thức của file: {instance.file.name} khỏi VectorDB")

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_chat_group(sender, instance, created, **kwargs):
    if created:
        group = ChatGroup.objects.create(
            name=f"Nhóm làm việc của {instance.username}",
            owner=instance
        )
        Membership.objects.create(
            user=instance,
            group=group,
            role='admin'
        )