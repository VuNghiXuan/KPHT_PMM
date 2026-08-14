"""
Module: ai_engine.py
Path: apps/ai_assistant/services/ai_engine.py
Description:
    Quản lý trung tâm cho Vector Store (ChromaDB / Extensible) và RAG pipeline,
    hỗ trợ KnowledgeChapter, Tenant Isolation (group_id) và async/sync wrappers.
"""

import logging
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class AIEngineService:
    """
    🧠 Dịch vụ lõi điều phối Vector Store và thao tác nhúng dữ liệu (Embedding & RAG).
    """

    def __init__(self):
        self.engine_type = getattr(settings, 'VECTOR_DB_ENGINE', 'chroma')
        self.client = self._init_vector_client()
        self.collection = self._get_or_create_collection()

    def _init_vector_client(self):
        """Khởi tạo client dựa trên cấu hình VECTOR_DB_ENGINE."""
        if self.engine_type == 'chroma':
            db_path = getattr(settings, 'VECTOR_DB_PATH', 'core/vector_db/')
            import chromadb
            return chromadb.PersistentClient(path=db_path)
        # 🔌 Sẵn sàng mở rộng cho Qdrant hoặc PGVector trong tương lai
        raise ValueError(f"Không hỗ trợ Vector DB Engine: {self.engine_type}")

    def _get_or_create_collection(self):
        """Lấy hoặc tạo collection chuẩn cho hệ thống vnxChatBot."""
        if self.engine_type == 'chroma':
            return self.client.get_or_create_collection(name="vnx_knowledge_chapters")
        return None

    def _sync_sync_chapter(self, chapter):
        """Đồng bộ đồng bộ hóa một KnowledgeChapter vào Vector Store."""
        # Bắt buộc đính kèm metadata group_id để cô lập dữ liệu tuyệt đối
        metadata = {
            "group_id": str(chapter.group_id),
            "chapter_id": chapter.id,
            "title": chapter.title,
            **(chapter.source_metadata or {})
        }
        
        # Thêm nội dung tóm tắt hoặc chi tiết chương vào Vector DB
        document_text = f"{chapter.title}\n{chapter.summary}"
        
        self.collection.upsert(
            ids=[f"chapter_{chapter.id}"],
            documents=[document_text],
            metadatas=[metadata]
        )
        logger.info(f"💾 [AIEngine] Đã đồng bộ thành công KnowledgeChapter ID: {chapter.id} vào {self.engine_type.upper()}")

    @classmethod
    def sync_chapter_embeddings(cls, chapter):
        """Phương thức gọi chính từ Celery Task để đồng bộ chapter."""
        instance = cls()
        instance._sync_sync_chapter(chapter)

    def _sync_remove_chapter(self, chapter_id: int):
        """Xóa vector embedding của một chương tri thức."""
        self.collection.delete(ids=[f"chapter_{chapter_id}"])
        logger.info(f"🗑️ [AIEngine] Đã gỡ bỏ vector cho KnowledgeChapter ID: {chapter_id}")

    @classmethod
    def remove_chapter_from_vector(cls, chapter_id: int):
        """Phương thức gọi chính khi xóa chapter."""
        instance = cls()
        instance._sync_remove_chapter(chapter_id)

    def _sync_query_vector(self, query: str, group_id: str, top_k: int = 3):
        """Truy vấn vector với bộ lọc bắt buộc theo group_id."""
        results = self.collection.query(
            query_texts=[query],
            where={"group_id": str(group_id)},
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

    async def query_vector_async(self, query: str, group_id: str, top_k: int = 3):
        """Truy vấn bất đồng bộ phục vụ cho luồng đọc (Read Side / RAG Chat)."""
        return await sync_to_async(self._sync_query_vector, thread_sensitive=False)(query, group_id, top_k)