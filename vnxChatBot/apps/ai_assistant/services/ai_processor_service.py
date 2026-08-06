"""
Mục đích: Facade Service điều phối luồng xử lý AI.
Quy trình: 
1. Trích xuất nội dung và gán điểm tin cậy (Confidence Score).
2. Quyết định duyệt tự động hoặc chờ xác nhận (Pending).
3. Đẩy dữ liệu vào Vector DB hoặc gửi thông báo admin.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models (KnowledgeUnit), apps.ai_assistant.vector_store
"""

from apps.group_chat.models import KnowledgeUnit
from apps.ai_assistant.vector_store import VectorDBManager
# Giả định các module xử lý AI lõi đã được định nghĩa tại đây
from apps.ai_assistant.engine import AI_Engine 
from apps.ai_assistant.services.notification import NotificationService

class AIProcessorService:
    
    @staticmethod
    def process_document_knowledge(unit_id):
        """
        Luồng xử lý kiến thức Hybrid:
        - Tự động hóa nếu độ tin cậy >= 0.9.
        - Chờ duyệt (Pending) nếu độ tin cậy < 0.9.
        """
        try:
            unit = KnowledgeUnit.objects.select_related('group', 'document').get(id=unit_id)
            
            # Gọi Engine trích xuất và gán điểm tin cậy
            content, confidence = AI_Engine.extract_and_score(unit.document.file.path)
            
            unit.content = content
            
            # Logic Hybrid Knowledge Lifecycle
            if confidence >= 0.9:
                unit.status = 'approved'
                # Đẩy vào Vector DB ngay lập tức
                AIProcessorService.sync_unit_to_vector(unit)
            else:
                unit.status = 'pending'
                # Notify Admin nhóm qua NotificationService
                NotificationService.notify_admin(
                    unit.group, 
                    f"Tri thức mới cần duyệt: {unit.entity_name} (Score: {confidence:.2f})"
                )
            
            unit.save()
            return True
        
        except KnowledgeUnit.DoesNotExist:
            return False
        except Exception as e:
            # Ghi log lỗi tại đây để kiến trúc sư theo dõi
            print(f"Error processing KnowledgeUnit {unit_id}: {str(e)}")
            return False

    @staticmethod
    def sync_unit_to_vector(knowledge_unit):
        """Đẩy dữ liệu vào Vector DB khi Unit được duyệt."""
        VectorDBManager.upsert_embedding(
            group_id=knowledge_unit.group.id,
            text=knowledge_unit.content,
            unit_id=knowledge_unit.id
        )

    @staticmethod
    def remove_unit_from_vector(knowledge_unit_id):
        """Xóa dữ liệu khỏi Vector DB khi Unit bị hủy/rollback."""
        VectorDBManager.remove_embedding(unit_id=knowledge_unit_id)

    @staticmethod
    def handle_manual_approval(unit_id):
        """
        Xử lý khi admin thực hiện duyệt thủ công một unit đang ở trạng thái 'pending'.
        """
        unit = KnowledgeUnit.objects.get(id=unit_id)
        unit.status = 'approved'
        unit.save()
        AIProcessorService.sync_unit_to_vector(unit)