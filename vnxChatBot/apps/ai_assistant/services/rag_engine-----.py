"""
Module: apps.ai_assistant.services.rag_engine
Author: Kiến trúc sư VnxChatBot & Senior Software Engineer
Description: Service xử lý RAG đã được tối ưu hóa luồng bất đồng bộ (async/await),
             bọc an toàn các thao tác ChromaDB và LLM bằng sync_to_async để tránh lỗi async context.
"""

from django.conf import settings
import chromadb
from asgiref.sync import sync_to_async
from .ai_factory import AIFactory

class RAGEngine:
    """
    Class: RAGEngine
    Description: 
        Quản lý việc tương tác với ChromaDB để lưu trữ, truy vấn 
        và sinh câu trả lời thông minh dựa trên tri thức nội bộ của từng nhóm làm việc (ChatGroup).
    """
    
    def __init__(self, group_id=None):
        """Khởi tạo kết nối PersistentClient tới ChromaDB dựa trên đường dẫn cấu hình."""
        self.group_id = group_id
        db_path = getattr(settings, 'VECTOR_DB_PATH', 'core/vector_db/')
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="vnx_knowledge")

    def _sync_get_all_active_knowledge(self, group_id: int):
        """Thực hiện get đồng bộ từ ChromaDB."""
        results = self.collection.get(
            where={"group_id": group_id}
        )
        return results.get('documents', [])

    async def get_all_active_knowledge(self, group_id: int):
        """Lấy toàn bộ kiến thức đã được duyệt của nhóm cụ thể (Tenant Isolation) bất đồng bộ."""
        return await sync_to_async(self._sync_get_all_active_knowledge, thread_sensitive=False)(group_id)

    def _sync_add_knowledge(self, knowledge_unit):
        """Thực hiện add đồng bộ vào ChromaDB."""
        self.collection.add(
            ids=[str(knowledge_unit.id)],
            documents=[knowledge_unit.content],
            metadatas=[{
                "entity": getattr(knowledge_unit, 'entity_name', ''),
                "context": getattr(knowledge_unit, 'context_tag', ''),
                "group_id": knowledge_unit.document.group.id
            }]
        )

    async def add_knowledge(self, knowledge_unit):
        """Nạp kiến thức đã được duyệt vào Vector DB kèm metadata bất đồng bộ."""
        await sync_to_async(self._sync_add_knowledge, thread_sensitive=False)(knowledge_unit)

    def _sync_remove_knowledge(self, knowledge_unit_id: int):
        """Thực hiện delete đồng bộ khỏi ChromaDB."""
        self.collection.delete(ids=[str(knowledge_unit_id)])

    async def remove_knowledge(self, knowledge_unit_id: int):
        """Xóa kiến thức khỏi Vector DB bất đồng bộ."""
        await sync_to_async(self._sync_remove_knowledge, thread_sensitive=False)(knowledge_unit_id)

    def _sync_query_knowledge(self, query: str, group_id: int, top_k: int = 3):
        """Thực hiện query đồng bộ từ ChromaDB."""
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

    async def query_knowledge_async(self, query: str, group_id: int, top_k: int = 3):
        """Truy vấn kiến thức nghiêm ngặt theo group_id từ ChromaDB bất đồng bộ."""
        return await sync_to_async(self._sync_query_knowledge, thread_sensitive=False)(query, group_id, top_k)

    async def query(self, query: str, top_k: int = 3) -> str:
        """
        Phương thức giao tiếp trực tiếp với Consumer, thực hiện quy trình RAG bất đồng bộ.
        """
        answer = await self.generate_rag_answer(group_id=self.group_id, query=query, top_k=top_k)
        return answer
    
    def build_rag_prompt(self, context_text: str, query: str) -> str:
        """Xây dựng prompt chuẩn cho mô hình LLM."""
        return f"Dựa vào tri thức nội bộ của nhóm sau đây:\n{context_text}\n\nCâu hỏi từ thành viên: {query}\nHãy trả lời ngắn gọn, chính xác và bám sát tri thức được cung cấp."

    async def generate_rag_answer(self, group_id: int, query: str, top_k: int = 3) -> str:
        """
        Sinh câu trả lời thông minh qua RAG hoàn toàn ở chế độ bất đồng bộ (async),
        bọc tất cả các lời gọi đồng bộ (ChromaDB, LLM) qua sync_to_async để triệt tiêu lỗi async context.
        """
        try:
            # 1. Truy vấn Vector DB lấy tri thức đặc thù theo group_id thông qua hàm bất đồng bộ
            context_docs = await self.query_knowledge_async(query=query, group_id=int(group_id), top_k=top_k)
            
            # 2. Xử lý và tổng hợp ngữ cảnh
            if context_docs:
                context_text = "\n".join([doc.get('content', '') for doc in context_docs])
            else:
                context_text = "Không có tài liệu tri thức liên quan trong hệ thống của nhóm."

            # 3. Xây dựng prompt
            prompt = self.build_rag_prompt(context_text=context_text, query=query)

            # 4. Khởi tạo LLM client thông qua AIFactory (Bọc sync_to_async nếu khởi tạo chạm DB)
            get_provider_async = sync_to_async(AIFactory.get_provider, thread_sensitive=False)
            llm_client = await get_provider_async(group_id=int(group_id))
            
            # 5. Sinh và trả về kết quả phản hồi từ mô hình AI an toàn
            if hasattr(llm_client, 'generate_async'):
                return await llm_client.generate_async(prompt)
            else:
                sync_generate = sync_to_async(llm_client.generate, thread_sensitive=False)
                return await sync_generate(prompt)
            
        except Exception as e:
            return f"Xin lỗi, trợ lý AI đang gặp sự cố khi truy vấn tri thức nhóm: {str(e)}"