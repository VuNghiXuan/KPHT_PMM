# apps/ai_assistant/vector_store/chromadb_client.py
import chromadb
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """
    Class quản lý kết nối và thao tác với ChromaDB.
    Tuân thủ nguyên tắc Singleton cho _client để tránh mở nhiều connection.
    """
    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            path = getattr(settings, 'VECTOR_DB_PATH', str(settings.BASE_DIR / "vector_data"))
            self._client = chromadb.PersistentClient(path=path)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(name="group_knowledge")
        return self._collection

    def upsert_embedding(self, group_id, text, unit_id):
        """
        Ghi đè hoặc thêm mới tri thức vào VectorDB.
        Đảm bảo tính nhất quán (Idempotency) dựa trên unit_id.
        """
        try:
            self.collection.upsert(
                documents=[text],
                metadatas=[{"group_id": str(group_id)}],
                ids=[str(unit_id)]
            )
        except Exception as e:
            logger.error(f"Lỗi khi upsert vào ChromaDB: {e}")

    def remove_embedding(self, unit_id):
        """Xóa tri thức khỏi VectorDB khi KnowledgeUnit bị rollback."""
        try:
            self.collection.delete(ids=[str(unit_id)])
        except Exception as e:
            logger.error(f"Lỗi khi xóa embedding {unit_id}: {e}")

# Export một instance duy nhất để các service sử dụng
VectorDBManager = ChromaDBClient()