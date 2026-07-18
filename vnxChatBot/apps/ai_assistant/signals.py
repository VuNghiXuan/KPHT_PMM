"""
Mục đích: Kết nối sự kiện Model (Upload/Delete) với logic AI & VectorDB.
Đã xử lý: Tránh đệ quy signal bằng cách kiểm tra created và sử dụng update().
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from apps.group_chat.models import Document, ChatGroup, Membership, KnowledgeUnit
from apps.ai_assistant.file_processor import extract_text_from_file
from apps.ai_assistant.vector_store import VectorDBManager as vector_service
from apps.ai_assistant.services.rag_engine import RAGEngine

@receiver(post_save, sender=Document)
def process_document_to_vector(sender, instance, created, **kwargs):
    # CHẶN ĐỆ QUY CỨNG: Chỉ chạy nếu đây là bản ghi mới (created=True)
    if not created:
        return

    if instance.file:
        try:
            text_content = extract_text_from_file(instance.file.path)
            if text_content:
                # 1. Nạp vào VectorDB
                vector_service.insert(
                    group_id=instance.group.id,
                    text=text_content,
                    doc_id=instance.id
                )
                
                # 2. Cập nhật metadata mà KHÔNG kích hoạt lại signal
                # .update() bypasses the model's save() method and signals
                Document.objects.filter(pk=instance.pk).update(processed_at=timezone.now())
                
                print(f"✅ Đã nạp tri thức vào VectorDB từ file: {instance.file.name}")
        except Exception as e:
            print(f"❌ Lỗi xử lý Vector cho file {instance.file.name}: {str(e)}")

@receiver(post_delete, sender=Document)
def remove_document_from_vector(sender, instance, **kwargs):
    try:
        vector_service.delete_document(doc_id=instance.id)
        print(f"🗑️ Đã xóa tri thức của file: {instance.file.name} khỏi VectorDB")
    except Exception as e:
        print(f"❌ Lỗi xóa vector cho file {instance.file.name}: {str(e)}")

@receiver(post_save, sender=KnowledgeUnit)
def handle_knowledge_approval(sender, instance, **kwargs):
    # LƯU Ý: RAGEngine không được gọi save() trên KnowledgeUnit bên trong hàm này
    engine = RAGEngine()
    try:
        if instance.status == 'approved':
            engine.add_knowledge(instance)
        elif instance.status == 'rollback':
            engine.remove_knowledge(instance.id)
    except Exception as e:
        print(f"❌ Lỗi RAG Engine: {str(e)}")

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

@receiver(post_save, sender=KnowledgeUnit)
def handle_knowledge_approval(sender, instance, **kwargs):
    engine = RAGEngine()
    try:
        if instance.status == 'approved':
            engine.add_knowledge(instance)
        elif instance.status == 'rollback':
            engine.remove_knowledge(instance.id)
    except Exception as e:
        print(f"❌ Lỗi RAG Engine: {str(e)}") # Log lỗi để theo dõi