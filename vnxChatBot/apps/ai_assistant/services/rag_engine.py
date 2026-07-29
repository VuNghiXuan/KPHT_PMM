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
    
    def __init__(self, group_id=None):
        """Khởi tạo kết nối PersistentClient tới ChromaDB dựa trên đường dẫn cấu hình."""
        self.group_id = group_id
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
            # ✅ Sửa 'metadantas' thành 'metadatas' và bám sát kiến trúc Group-Centric
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

    async def query(self, query: str, top_k: int = 3) -> str:
        """
        Phương thức giao tiếp trực tiếp với Consumer, thực hiện quy trình RAG 
        bao gồm truy vấn Vector DB theo group_id và sinh câu trả lời qua LLM.
        
        Args:
            query (str): Câu hỏi từ người dùng gửi qua WebSocket.
            top_k (int): Số lượng kết quả tài liệu tối đa cần lấy từ VectorStore.
            
        Returns:
            str: Câu trả lời hoàn chỉnh được tổng hợp từ AI Assistant dựa trên ngữ cảnh nhóm.
        
        Why:
            Phương thức được định nghĩa là `async def` để tương thích hoàn toàn với vòng lặp 
            sự kiện bất đồng bộ (async event loop) của Django Channels (`ChatConsumer`), 
            giúp tránh nghẽn luồng (blocking) khi gọi các tác vụ I/O nặng như truy vấn Vector DB 
            và gọi API LLM từ xa.
        """
        # Sử dụng lại phương thức generate_rag_answer đã được tích hợp sẵn group_id (Tenant Isolation)
        # Nếu generate_rag_answer là hàm đồng bộ, ta dùng asgiref.sync.sync_to_async để bọc an toàn.
        # Ở đây giả lập gọi trực tiếp bất đồng bộ hoặc thông qua sync_to_async tùy thuộc vào implementation của RAGEngine.
        
        # Gọi trực tiếp vì hàm query đã là async def
        answer = await self.generate_rag_answer(group_id=self.group_id, query=query, top_k=top_k)
        
        return answer
    
    
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
    def generate_rag_answer(self, group_id: int, query: str, top_k: int = 3) -> str:
        """
        Sinh câu trả lời thông minh qua RAG (Retrieval-Augmented Generation) 
        tuân thủ tuyệt đối quy tắc Tenant Isolation theo group_id.

        Args:
            group_id (int): Định danh duy nhất của nhóm làm việc (ChatGroup).
            query (str): Câu hỏi hoặc thông điệp cần truy vấn từ người dùng.
            top_k (int): Số lượng kết quả tài liệu tối đa cần trích xuất từ Vector DB.

        Returns:
            str: Câu trả lời hoàn chỉnh được sinh ra từ LLM dựa trên ngữ cảnh tri thức của nhóm.
            
        Why:
            - Sử dụng `@database_sync_to_async` để gói gọn các tác vụ kết nối ORM/Database 
              an toàn trong môi trường bất đồng bộ của Django Channels.
            - Phân lập dữ liệu tri thức theo `group_id` giúp bảo mật tuyệt đối, ngăn chặn 
              việc rò rỉ thông tin giữa các nhóm khác nhau trong hệ thống Modular Monolith.
            - Tích hợp `AIFactory` để linh hoạt thay đổi nhà cung cấp LLM (OpenAI, Gemini, Groq, Ollama) 
              dựa trên cấu hình riêng biệt của từng nhóm.
        """
        try:
            # 1. Truy vấn Vector DB lấy tri thức đặc thù theo group_id (Bảo mật Tenant Isolation)
            context_docs = self.query_knowledge(query=query, group_id=int(group_id), top_k=top_k)
            
            # 2. Xử lý và tổng hợp ngữ cảnh (Context Aggregation)
            if context_docs:
                context_text = "\n".join([doc.get('content', '') for doc in context_docs])
            else:
                context_text = "Không có tài liệu tri thức liên quan trong hệ thống của nhóm."

            # 3. Gọi hàm dựng prompt đã được tối ưu hóa để định hình phong cách trả lời cho AI
            prompt = self.build_rag_prompt(context_text=context_text, query=query)

            # 4. Khởi tạo LLM client thông qua AIFactory (Bảo mật API Key & Tùy biến Provider theo nhóm)
            llm_client = AIFactory.get_provider(group_id=int(group_id))
            
            # 5. Sinh và trả về kết quả phản hồi từ mô hình AI
            return llm_client.generate(prompt)
            
        except Exception as e:
            # Xử lý ngoại lệ an toàn, đảm bảo hệ thống không bị crash đột ngột tại luồng WebSocket
            return f"Xin lỗi, trợ lý AI đang gặp sự cố khi truy vấn tri thức nhóm: {str(e)}"