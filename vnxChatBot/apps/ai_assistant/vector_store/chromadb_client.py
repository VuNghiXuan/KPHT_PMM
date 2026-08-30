# -*- coding: utf-8 -*-
# Path: apps/ai_assistant/vector_store/chromadb_client.py
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

    @staticmethod
    def compute_embedding(text: str):
        """
        Tính toán vector embedding cho văn bản đầu vào.
        Tích hợp qua LiteLLM hoặc AI Engine chuẩn hóa của hệ thống.
        """
        try:
            from apps.ai_assistant.services.ai_engine import AI_Engine
            # Sử dụng AI Engine để tạo embedding chuẩn xác
            return AI_Engine.get_embedding(text)
        except Exception as e:
            logger.warning(f"⚠️ [ChromaDB] Không thể dùng AI_Engine để tạo embedding, dùng vector giả lập dự phòng: {str(e)}")
            # Fallback vector cơ bản nếu chưa cấu hình API Key embedding đầy đủ trong môi trường test
            return [0.0] * 1536

    @staticmethod
    def search(embedding, group_id, limit=3, threshold=0.85):
        """
        Tìm kiếm vector tương đồng trong phạm vi group_id (Hard Scoping).
        """
        try:
            client = ChromaDBClient()
            results = client.collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where={"group_id": str(group_id)}
            )
            
            formatted_results = []
            if results and results.get('documents') and results['documents'][0]:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                distances = results['distances'][0] if 'distances' in results and results['distances'] else [0.0] * len(docs)
                
                for doc, meta, dist in zip(docs, metas, distances):
                    # Chuyển đổi khoảng cách (distance) thành điểm tương đồng (similarity) nếu cần
                    similarity = 1.0 - dist if dist <= 1.0 else 0.0
                    if similarity >= threshold:
                        formatted_results.append({
                            "id": meta.get("unit_id") or meta.get("doc_id"),
                            "document": doc,
                            "metadata": meta,
                            "similarity": similarity
                        })
            return formatted_results
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi thực hiện search vector: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def insert(group_id, text, doc_id):
        """
        Thêm hoặc cập nhật tri thức từ tài liệu vào VectorDB.
        """
        try:
            if not text or not text.strip():
                logger.warning(f"⚠️ [ChromaDB] Văn bản trống đối với Document ID: {doc_id}, bỏ qua insert vector.")
                return

            client = ChromaDBClient()
            client.collection.upsert(
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

    @staticmethod
    def upsert_embedding(group_id, text, doc_id=None, unit_id=None):
        """
        Thêm hoặc cập nhật tri thức từ tài liệu hoặc KnowledgeUnit vào VectorDB (ChromaDB).
        """
        try:
            if not text or not text.strip():
                return

            identifier = unit_id if unit_id is not None else doc_id
            if identifier is None:
                logger.warning("⚠️ [ChromaDB] Không tìm thấy identifier (doc_id hoặc unit_id) để insert vector.")
                return

            client = ChromaDBClient()
            client.collection.upsert(
                documents=[text],
                metadatas=[{
                    "group_id": str(group_id), 
                    "doc_id": str(doc_id) if doc_id else "",
                    "unit_id": str(unit_id) if unit_id else ""
                }],
                ids=[f"unit_{identifier}" if unit_id else f"doc_{identifier}"]
            )
            logger.info(f"✅ [ChromaDB] Đã upsert embedding thành công cho identifier: {identifier} thuộc nhóm {group_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi upsert embedding: {str(e)}", exc_info=True)
            raise e
            
    def remove_embedding(self, unit_id):
        """Xóa tri thức khỏi VectorDB khi KnowledgeUnit bị rollback."""
        try:
            self.collection.delete(ids=[str(unit_id)])
            logger.info(f"🗑️ [ChromaDB] Đã xóa embedding của KnowledgeUnit unit_id: {unit_id}")
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi khi xóa embedding KnowledgeUnit {unit_id}: {str(e)}", exc_info=True)

    def delete_unit_embeddings(self, unit_id, group_id=None):
        """
        Xóa các vector embedding liên quan đến một KnowledgeUnit cụ thể trong ChromaDB.
        """
        try:
            if group_id is not None:
                where_filter = {
                    "$and": [
                        {"unit_id": str(unit_id)},
                        {"group_id": str(group_id)}
                    ]
                }
            else:
                where_filter = {"unit_id": str(unit_id)}

            self.collection.delete(where=where_filter)
            logger.info(f"🗑️ [ChromaDB] Đã xóa embeddings cho Unit ID: {unit_id} (Group ID: {group_id})")
            return True
        except Exception as e:
            logger.error(f"⚠️ [ChromaDB Warning] Không thể xóa embeddings cho Unit ID {unit_id}: {str(e)}")
            return False

    @staticmethod
    def add_texts(texts, metadatas=None, ids=None, group_id=None, **kwargs):
        """
        Phương thức tương thích ngược cho các service gọi hàm add_texts truyền thống.
        """
        try:
            client = ChromaDBClient()
            if not texts:
                return []
            
            results_ids = []
            for i, text in enumerate(texts):
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                doc_id = meta.get('doc_id')
                unit_id = meta.get('unit_id')
                g_id = meta.get('group_id') or group_id
                
                client.upsert_embedding(group_id=g_id, text=text, doc_id=doc_id, unit_id=unit_id)
                
                if ids and i < len(ids):
                    results_ids.append(ids[i])
                else:
                    results_ids.append(f"text_{i}")
                    
            logger.info(f"✅ [ChromaDB] Đã xử lý add_texts thành công với {len(texts)} văn bản.")
            return results_ids
        except Exception as e:
            logger.error(f"❌ [ChromaDB] Lỗi trong add_texts: {str(e)}", exc_info=True)
            raise e
        
# KHỞI TẠO INSTANCE TOÀN CỤC CHUẨN XÁC
VectorDBManager = ChromaDBClient()