"""
Mục đích: Service xử lý RAG (Retrieval-Augmented Generation).
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.conf import settings
import chromadb

class RAGEngine:
    def __init__(self):
        db_path = getattr(settings, 'VECTOR_DB_PATH', 'core/vector_db/')
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="vnx_knowledge")

    def get_all_active_knowledge(self, group_id: int):
        """
        Lấy toàn bộ kiến thức đã được duyệt (approved) của một nhóm cụ thể.
        Tại sao (Why): Phục vụ cho việc kiểm tra, quản lý hoặc tóm tắt kiến thức 
        của nhóm mà không làm lộ dữ liệu của nhóm khác.
        """
        # Sử dụng where filter để đảm bảo Tenant Isolation
        results = self.collection.get(
            where={"group_id": group_id}
        )
        
        # Trả về danh sách nội dung kiến thức
        return results.get('documents', [])

    def add_knowledge(self, knowledge_unit):
        """
        Nạp kiến thức đã được duyệt vào Vector DB kèm metadata để phân loại (Conflict Resolution).
        """
        self.collection.add(
            ids=[str(knowledge_unit.id)],
            documents=[knowledge_unit.content],
            metadatas=[{
                "entity": knowledge_unit.entity_name,
                "context": knowledge_unit.context_tag,
                "group_id": knowledge_unit.document.group.id
            }]
        )

    def remove_knowledge(self, knowledge_unit_id: int):
        """
        Xóa kiến thức khỏi Vector DB khi status chuyển về Rollback.
        """
        self.collection.delete(ids=[str(knowledge_unit_id)])

    def query_knowledge(self, query: str, group_id: int, top_k: int = 3):
        """
        Truy vấn kiến thức nghiêm ngặt theo group_id (Tenant Isolation).
        """
        return self.collection.query(
            query_texts=[query],
            where={"group_id": group_id},
            n_results=top_k
        )