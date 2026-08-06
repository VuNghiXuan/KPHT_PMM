"""
File: apps/ai_assistant/vector_store/chromadb_client.py
Mục đích: Cung cấp lớp giao tiếp với ChromaDB để quản lý Vector Embedding cho hệ thống RAG, 
          hỗ trợ phân tách dữ liệu theo nhóm (Group-Centric) và Vòng đời tri thức (Knowledge Lifecycle).
Tác giả: Kỹ sư kiến trúc vnxChatBot
Module liên kết: apps.ai_assistant, django.conf
"""

import os
import chromadb
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """
    Class: ChromaDBClient
    Description: Quản lý kết nối và thao tác lưu trữ Vector với ChromaDB. 
                 Áp dụng thiết kế Singleton để tối ưu hóa tài nguyên kết nối, 
                 đảm bảo gắn chặt metadata group_id nhằm cô lập dữ liệu tenant.
    """
    
    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Khởi tạo hoặc trả về ChromaDB PersistentClient một cách an toàn."""
        if self._client is None:
            path = getattr(settings, 'VECTOR_DB_PATH', str(settings.BASE_DIR / "vector_data"))
            os.makedirs(path, exist_ok=True)
            try:
                self._client = chromadb.PersistentClient(path=path)
                logger.info(f"📂 [ChromaDB] Khởi tạo PersistentClient thành công tại đường dẫn: {path}")
            except Exception as e:
                logger.error(f"❌ [ChromaDB] Không thể khởi tạo PersistentClient: {str(e)}")
                raise e
        return self._client

    @property
    def collection(self):
        """Lấy hoặc khởi tạo collection mặc định 'group_knowledge'."""
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(name="group_knowledge")
                logger.info("📦 [ChromaDB] Đã kết nối thành công tới collection 'group_knowledge'")
            except Exception as e:
                logger.error(f"❌ [ChromaDB] Lỗi khi tạo hoặc lấy collection: {str(e)}")
                raise e
        return self._collection

    def insert(self, group_id, text, doc_id):
        """
        Thêm hoặc cập nhật tri thức từ tài liệu vào VectorDB.
        
        Args:
            group_id (int|str): ID định danh nhóm (Tenant isolation).
            text (str): Nội dung văn bản cần nhúng vector.
            doc_id (int|str): ID định danh tài liệu (Document ID).
        """
        try:
            if not text or not text.strip():
                logger.warning(f"⚠️ [ChromaDB] Văn bản trống đối với Document ID: {doc_id}, bỏ qua insert vector.")
                return

            self.collection.upsert(
                documents=[text],
                metadatas=[{"group_id": str(group_id), "doc_id": str(doc_id)}],
                ids=[f"doc_{doc_id}"]
            )
            logger.info(f"✅ [ChromaDB] Đã insert thành công vector cho Document ID: {doc_id} vào nhóm {group_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi chi tiết khi insert Document ID {doc_id} vào ChromaDB: {str(e)}", exc_info=True)
            raise e

    def delete_document(self, doc_id):
        """Xóa vector của tài liệu khỏi VectorDB khi Document bị xóa (Garbage Collection)."""
        try:
            self.collection.delete(ids=[f"doc_{doc_id}"])
            logger.info(f"🗑️ [ChromaDB] Đã xóa vector của Document ID: {doc_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi xóa vector Document ID {doc_id}: {str(e)}", exc_info=True)

    def upsert_embedding(self, group_id, text, unit_id):
        """
        Ghi đè hoặc thêm mới tri thức KnowledgeUnit vào VectorDB (Phục vụ Knowledge Lifecycle).
        """
        try:
            if not text or not text.strip():
                logger.warning(f"⚠️ [ChromaDB] Nội dung KnowledgeUnit ID {unit_id} trống, bỏ qua upsert.")
                return

            self.collection.upsert(
                documents=[text],
                metadatas=[{"group_id": str(group_id), "type": "knowledge_unit"}],
                ids=[str(unit_id)]
            )
            logger.info(f"✅ [ChromaDB] Đã upsert thành công KnowledgeUnit ID: {unit_id} vào nhóm {group_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi chi tiết khi upsert KnowledgeUnit ID {unit_id}: {str(e)}", exc_info=True)
            raise e
            
    def remove_embedding(self, unit_id):
        """Xóa tri thức khỏi VectorDB khi KnowledgeUnit bị rollback."""
        try:
            self.collection.delete(ids=[str(unit_id)])
            logger.info(f"🗑️ [ChromaDB] Đã xóa embedding của KnowledgeUnit unit_id: {unit_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi xóa embedding KnowledgeUnit {unit_id}: {str(e)}", exc_info=True)


# KHỞI TẠO INSTANCE TOÀN CỤC CHUẨN XÁC (Tránh lỗi gọi nhầm Class)
VectorDBManager = ChromaDBClient()