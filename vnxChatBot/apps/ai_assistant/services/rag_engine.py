"""
Mục đích: Service xử lý RAG (Retrieval-Augmented Generation).
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.ai_assistant.services.ai_factory, chromadb
"""

from django.conf import settings
import chromadb
from channels.db import database_sync_to_async
from .ai_factory import AIFactory

class RAGEngine:
    """
    Class: RAGEngine
    Description: 
        Quản lý việc tương tác trực tiếp với ChromaDB để lưu trữ, truy vấn 
        và sinh câu trả lời thông minh dựa trên tri thức nội bộ của từng nhóm làm việc (ChatGroup).
    """
    
    def __init__(self):
        """Khởi tạo kết nối PersistentClient tới ChromaDB dựa trên đường dẫn cấu hình."""
        db_path = getattr(settings, 'VECTOR_DB_PATH', 'core/vector_db/')
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="vnx_knowledge")

    def get_all_active_knowledge(self, group_id: int):
        """
        Lấy toàn bộ kiến thức đã được duyệt (approved) của một nhóm cụ thể.
        Tại sao (Why): Phục vụ cho việc kiểm tra, quản lý hoặc tóm tắt kiến thức 
        của nhóm mà không làm lộ dữ liệu của nhóm khác (Tenant Isolation).
        
        Args:
            group_id (int): Định danh nhóm làm việc.
            
        Returns:
            list: Danh sách nội dung tài liệu tri thức.
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
        
        Args:
            knowledge_unit: Đối tượng KnowledgeUnit chứa nội dung và metadata cần nạp.
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
        
        Args:
            knowledge_unit_id (int): ID của đơn vị kiến thức cần xóa khỏi Vector Store.
        """
        self.collection.delete(ids=[str(knowledge_unit_id)])

    def query_knowledge(self, query: str, group_id: int, top_k: int = 3):
        """
        Truy vấn kiến thức nghiêm ngặt theo group_id (Tenant Isolation).
        Trích xuất và định dạng kết quả từ ChromaDB thành danh sách các dictionary.
        
        Args:
            query (str): Câu truy vấn từ người dùng.
            group_id (int): Định danh nhóm (Tenant ID).
            top_k (int): Số lượng kết quả phù hợp tối đa cần lấy.
            
        Returns:
            list[dict]: Danh sách chứa nội dung và metadata của các đoạn tri thức phù hợp.
        """
        results = self.collection.query(
            query_texts=[query],
            where={"group_id": group_id},
            n_results=top_k
        )
        
        formatted_results = []
        documents = results.get('documents', [[]])
        metadatas = results.get('metadatas', [[]])
        
        if documents and documents[0]:
            for doc, meta in zip(documents[0], metadatas[0]):
                formatted_results.append({
                    'content': doc,
                    'metadata': meta
                })
                
        return formatted_results
    
    def build_rag_prompt(self, context_text: str, query: str) -> str:
        """
        Xây dựng prompt chuẩn cho mô hình LLM dựa trên tri thức nội bộ và câu hỏi.
        
        Args:
            context_text (str): Nội dung tri thức đã được trích xuất từ Vector DB.
            query (str): Câu hỏi thực tế từ thành viên trong nhóm.
            
        Returns:
            str: Chuỗi prompt hoàn chỉnh đã được định hình.
        """
        return f"Dựa vào tri thức nội bộ của nhóm sau đây:\n{context_text}\n\nCâu hỏi từ thành viên: {query}\nHãy trả lời ngắn gọn, chính xác và bám sát tri thức được cung cấp."

    @database_sync_to_async
    def generate_rag_answer(self, group_id: int, query: str) -> str:
        """
        Sinh câu trả lời thông minh qua RAG tuân thủ tuyệt đối quy tắc Tenant Isolation.
        """
        try:
            # 1. Truy vấn Vector DB lấy tri thức theo group_id
            context_docs = self.query_knowledge(query=query, group_id=int(group_id), top_k=3)
            
            # 2. Xử lý ngữ cảnh (Context)
            context_text = "\n".join([doc['content'] for doc in context_docs]) if context_docs else "Không có tài liệu tri thức liên quan trong hệ thống."

            # 3. Gọi hàm dựng prompt đã tối ưu (Thoát khỏi việc lặp code)
            prompt = self.build_rag_prompt(context_text=context_text, query=query)

            # 4. Gọi LLM thông qua AIFactory để đảm bảo bảo mật và linh hoạt Provider
            llm_client = AIFactory.get_provider(group_id=int(group_id))
            return llm_client.generate(prompt)
            
        except Exception as e:
            return f"Xin lỗi, trợ lý AI đang gặp sự cố khi truy vấn tri thức nhóm: {str(e)}"