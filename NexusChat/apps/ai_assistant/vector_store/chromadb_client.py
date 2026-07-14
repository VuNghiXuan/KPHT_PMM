import chromadb
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ChromaDBClient:
    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Khởi tạo client chỉ khi thực sự cần thiết (Lazy Loading)."""
        if self._client is None:
            # Truy cập settings tại thời điểm gọi, tránh lỗi khi startup Django
            self._client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        return self._client

    @property
    def collection(self):
        """Lấy hoặc tạo collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(name="group_knowledge")
        return self._collection

    def insert(self, group_id, text, doc_id):
        """Thêm tài liệu với metadata group_id."""
        try:
            self.collection.add(
                documents=[text],
                metadatas=[{"group_id": str(group_id)}],
                ids=[f"doc_{doc_id}"]
            )
        except Exception as e:
            logger.error(f"Lỗi khi insert vào ChromaDB: {e}")

    def search(self, group_id, query_text):
        """Tìm tài liệu liên quan trong phạm vi nhóm."""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                where={"group_id": str(group_id)},
                n_results=3
            )
            # Trả về list documents hoặc list rỗng
            return results.get('documents', [[]])[0] if results.get('documents') else []
        except Exception as e:
            logger.error(f"Lỗi khi query ChromaDB: {e}")
            return []

    def delete_document(self, doc_id):
        """Xóa tài liệu cụ thể."""
        try:
            self.collection.delete(ids=[f"doc_{doc_id}"])
        except Exception as e:
            logger.error(f"Lỗi khi xóa doc {doc_id}: {e}")

    def delete_group_data(self, group_id):
        """Xóa toàn bộ dữ liệu của một nhóm."""
        try:
            self.collection.delete(where={"group_id": str(group_id)})
        except Exception as e:
            logger.error(f"Lỗi khi xóa dữ liệu nhóm {group_id}: {e}")

    def get_collection_stats(self):
        """Kiểm tra số lượng tài liệu."""
        return self.collection.count()

# Khởi tạo class, nhưng CHƯA truy cập settings.VECTOR_DB_PATH ngay tại đây
db_client = ChromaDBClient()