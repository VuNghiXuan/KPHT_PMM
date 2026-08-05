# apps/ai_assistant/vector_store/chromadb_client.py
import os
import chromadb
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """
    Class quản lý kết nối và thao tác với ChromaDB.
    Tuân thủ nguyên tắc Singleton cho _client để tránh mở nhiều connection.
    Hỗ trợ cô lập dữ liệu theo nhóm (Group-Centric) qua metadata group_id.
    """
    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Khởi tạo hoặc trả về ChromaDB PersistentClient."""
        if self._client is None:
            path = getattr(settings, 'VECTOR_DB_PATH', str(settings.BASE_DIR / "vector_data"))
            os.makedirs(path, exist_ok=True)
            self._client = chromadb.PersistentClient(path=path)
        return self._client

    @property
    def collection(self):
        """Lấy hoặc khởi tạo collection mặc định 'group_knowledge'."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(name="group_knowledge")
        return self._collection

    def insert(self, group_id, text, doc_id):
        """
        Thêm hoặc cập nhật tri thức từ tài liệu vào VectorDB.
        Gắn kèm metadata group_id để đảm bảo cô lập dữ liệu giữa các nhóm (Group-Centric).
        """
        try:
            self.collection.upsert(
                documents=[text],
                metadatas=[{"group_id": str(group_id), "doc_id": str(doc_id)}],
                ids=[f"doc_{doc_id}"]
            )
            logger.info(f"✅ [ChromaDB] Đã insert thành công vector cho Document ID: {doc_id} vào nhóm {group_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi insert vào ChromaDB: {e}")
            raise e

    def delete_document(self, doc_id):
        """Xóa vector của tài liệu khỏi VectorDB khi Document bị xóa (Garbage Collection)."""
        try:
            self.collection.delete(ids=[f"doc_{doc_id}"])
            logger.info(f"🗑️ [ChromaDB] Đã xóa vector của Document ID: {doc_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi xóa vector Document ID {doc_id}: {e}")

    @staticmethod
    def upsert_embedding(group_id, text, unit_id):
        """Ghi đè hoặc thêm mới tri thức KnowledgeUnit vào VectorDB."""
        try:
            client = get_vector_store()
            collection = client.get_or_create_collection(name="group_knowledge")
            collection.upsert(
                documents=[text],
                metadatas=[{"group_id": str(group_id)}],
                ids=[str(unit_id)]
            )
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi upsert KnowledgeUnit: {e}")
            
    def remove_embedding(self, unit_id):
        """Xóa tri thức khỏi VectorDB khi KnowledgeUnit bị rollback."""
        try:
            self.collection.delete(ids=[str(unit_id)])
            logger.info(f"🗑️ [ChromaDB] Đã xóa embedding của unit_id: {unit_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi xóa embedding {unit_id}: {e}")

def get_vector_store():
    """Khởi tạo và trả về ChromaDB PersistentClient."""
    db_path = getattr(settings, 'VECTOR_DB_PATH', os.path.join(settings.BASE_DIR, 'core', 'vector_db'))
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path)

# Export instance toàn cục
VectorDBManager = ChromaDBClient()