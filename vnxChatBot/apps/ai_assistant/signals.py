"""
Module: ai_assistant.signals
Author: Kỹ sư Phần mềm Cao cấp / Kiến trúc trưởng VnxChatBot
Description: Kết nối sự kiện Model (Upload/Delete/Update) với logic AI & VectorDB.
             Đã xử lý: Tránh đệ quy signal, chống rác hệ thống (Garbage Collection), 
             và tự động hóa vòng đời tri thức (Knowledge Lifecycle) từ Document đến VectorStore.
"""

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from apps.group_chat.models import Document, ChatGroup, Membership, KnowledgeUnit
from apps.ai_assistant.file_processor import extract_text_from_file
from apps.ai_assistant.vector_store import VectorDBManager as vector_service
from apps.ai_assistant.services.rag_engine import RAGEngine


@receiver(post_save, sender=Document)
def process_document_to_vector(sender, instance, created, **kwargs):
    """
    Lắng nghe sự kiện khi một Document mới được tải lên nhóm.
    
    Args:
        sender (Model): Model Document phát ra tín hiệu.
        instance (Document): Thực thể tài liệu vừa được tạo.
        created (bool): Cờ kiểm tra bản ghi mới tạo hay cập nhật.
    
    Logic:
        Chặn đệ quy cứng, tự động trích xuất văn bản từ file, đẩy vào VectorDB 
        theo phạm vi group_id (Group-Centric) và cập nhật mốc thời gian xử lý.
    """
    if not created:
        return

    if instance.file:
        try:
            text_content = extract_text_from_file(instance.file.path)
            if text_content:
                # 1. Nạp nội dung vào VectorDB theo phạm vi group_id tenant
                vector_service.insert(
                    group_id=instance.group.id,
                    text=text_content,
                    doc_id=instance.id
                )
                
                # 2. Cập nhật metadata mà KHÔNG kích hoạt lại vòng lặp save() hay signal
                Document.objects.filter(pk=instance.pk).update(processed_at=timezone.now())
                
                print(f"✅ Đã nạp tri thức vào VectorDB từ file: {instance.file.name}")
        except Exception as e:
            print(f"❌ Lỗi xử lý Vector cho file {instance.file.name}: {str(e)}")


@receiver(post_delete, sender=Document)
def remove_document_from_vector(sender, instance, **kwargs):
    """
    Dọn dẹp VectorDB khi một Document bị xóa hoàn toàn khỏi hệ thống,
    đảm bảo nguyên tắc chống rác (Garbage Collection)[cite: 1].
    """
    try:
        vector_service.delete_document(doc_id=instance.id)
        print(f"🗑️ Đã xóa tri thức của file: {instance.file.name} khỏi VectorDB[cite: 1]")
    except Exception as e:
        print(f"❌ Lỗi xóa vector cho file {instance.file.name}: {str(e)}")


@receiver(post_save, sender=KnowledgeUnit)
def handle_knowledge_unit_lifecycle(sender, instance, **kwargs):
    """
    Lắng nghe thay đổi trạng thái của KnowledgeUnit (Knowledge Lifecycle).
    
    Logic:
        - 'approved': Phê duyệt tri thức, thêm vào RAG Engine / Vector DB[cite: 1].
        - 'rolled_back' hoặc 'rollback': Thu hồi, xóa embedding tương ứng[cite: 1].
    """
    engine = RAGEngine()
    try:
        if instance.status == 'approved':
            engine.add_knowledge(instance)
            print(f"✅ KnowledgeUnit #{instance.id} đã được phê duyệt và đồng bộ vào Vector DB[cite: 1].")
        elif instance.status in ['rolled_back', 'rollback']:
            engine.remove_knowledge(instance.id)
            print(f"🔄 KnowledgeUnit #{instance.id} đã bị thu hồi (Rolled Back)[cite: 1].")
    except Exception as e:
        print(f"❌ Lỗi RAG Engine khi xử lý KnowledgeUnit #{instance.id}: {str(e)}")


@receiver(pre_delete, sender=KnowledgeUnit)
def handle_knowledge_unit_cleanup(sender, instance, **kwargs):
    """
    Xóa sạch embedding liên quan trong Vector Store ngay trước khi 
    KnowledgeUnit bị xóa vĩnh viễn khỏi cơ sở dữ liệu[cite: 1].
    """
    try:
        engine = RAGEngine()
        engine.remove_knowledge(instance.id)
        print(f"🗑️ Đã dọn dẹp tri thức vĩnh viễn của KnowledgeUnit #{instance.id} khỏi Vector DB[cite: 1].")
    except Exception as e:
        print(f"❌ Lỗi khi dọn dẹp KnowledgeUnit #{instance.id}: {str(e)}")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_chat_group_for_new_user(sender, instance, created, **kwargs):
    """
    Tự động khởi tạo Nhóm làm việc riêng cho User mới đăng ký,
    tuân thủ đúng quy tắc User tự chủ động tạo nhóm/quản lý nhóm 
    và mô hình cô lập dữ liệu theo nhóm (Group-Centric).
    """
    if created:
        # Khởi tạo ChatGroup độc lập không chứa trường created_by thừa thãi
        group = ChatGroup.objects.create(
            name=f"Nhóm làm việc của {instance.username}"
        )
        
        # Gán quyền quản trị (admin) cho người dùng mới trong nhóm thông qua Membership
        Membership.objects.create(
            user=instance,
            group=group,
            role='admin'
        )
        
        print(f"👥 Đã khởi tạo nhóm mặc định cho user mới: {instance.username}[cite: 1]")