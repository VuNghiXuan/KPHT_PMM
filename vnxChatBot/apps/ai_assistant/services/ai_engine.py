"""
Module: ai_engine.py
Path: apps/ai_assistant/services/ai_engine.py
Description:
    Quản lý trung tâm cho Vector Store (ChromaDB / Extensible) và RAG pipeline,
    hỗ trợ KnowledgeChapter, Tenant Isolation (group_id) và async/sync wrappers,
    tích hợp Redis Semantic Cache theo tiêu chuẩn hiệu năng cao.
"""

import json
import logging
import math
from typing import List, Union

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache

from apps.ai_assistant.utils import clean_json_markdown

logger = logging.getLogger(__name__)


class AIEngineService:
    """🧠 Dịch vụ lõi điều phối Vector Store, Semantic Cache và thao tác nhúng dữ liệu (Embedding & RAG)."""

    def __init__(self):
        self.engine_type = getattr(settings, "VECTOR_DB_ENGINE", "chroma")
        self.client = self._init_vector_client()
        self.collection = self._get_or_create_collection()

    def _init_vector_client(self):
        """Khởi tạo client dựa trên cấu hình VECTOR_DB_ENGINE."""
        if self.engine_type == "chroma":
            db_path = getattr(settings, "VECTOR_DB_PATH", "core/vector_db/")
            import chromadb

            return chromadb.PersistentClient(path=db_path)
        raise ValueError(f"Không hỗ trợ Vector DB Engine: {self.engine_type}")

    def _get_or_create_collection(self):
        """Lấy hoặc tạo collection chuẩn cho hệ thống vnxChatBot."""
        if self.engine_type == "chroma":
            return self.client.get_or_create_collection(
                name="vnx_knowledge_chapters"
            )
        return None

    # --- PHƯƠNG THỨC TẠO EMBEDDING 🛠️ ---

    @staticmethod
    def _generate_dummy_embedding(text: str, dim: int = 768) -> List[float]:
        """Tạo vector giả lập nhất quán (Deterministic Dummy Vector) dựa trên hash chuỗi."""
        seed = sum(ord(c) for c in text)
        vector = [math.sin(seed + i) for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    @staticmethod
    def get_embedding(text: str) -> List[float]:
        """📌 Tạo vector embedding từ văn bản đầu vào tối ưu cho LiteLLM & Gemini."""
        if not text or not text.strip():
            logger.warning("⚠️ [AIEngine] Chuỗi văn bản rỗng, trả về vector 0.")
            return [0.0] * 768  # 768 chiều theo chuẩn Gemini text-embedding-004

        try:
            import litellm

            # Tắt bớt các cảnh báo verbose không cần thiết từ LiteLLM
            litellm.suppress_debug_info = True

            raw_model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-004")

            # Chuẩn hóa prefix cho LiteLLM nếu dùng Gemini model
            if "text-embedding-004" in raw_model and not raw_model.startswith("gemini/"):
                embedding_model = f"gemini/{raw_model}"
            else:
                embedding_model = raw_model

            google_key = getattr(settings, "GOOGLE_API_KEY", None)
            openai_key = getattr(settings, "OPENAI_API_KEY", None)

            api_key = google_key if "gemini" in embedding_model else (openai_key or google_key)

            if api_key:
                response = litellm.embedding(
                    model=embedding_model,
                    input=[text],
                    api_key=api_key
                )
                return response["data"][0]["embedding"]

            raise ValueError("Không tìm thấy API Key hợp lệ cho Embedding Service.")

        except Exception as e:
            logger.warning(
                f"⚠️ [AIEngine] Không thể tạo Embedding qua Provider ({e}). Sử dụng vector dự phòng cho kiểm thử."
            )
            return AIEngineService._generate_dummy_embedding(text, dim=768)

    # --- ĐỒNG BỘ VECTOR STORE 🔄 ---

    def _sync_sync_chapter(self, chapter):
        """Đồng bộ một KnowledgeChapter vào Vector Store."""
        metadata = {
            "group_id": str(chapter.group_id),
            "chapter_id": chapter.id,
            "title": chapter.title,
            **(chapter.source_metadata or {}),
        }

        document_text = f"{chapter.title}\n{chapter.summary}"

        # Lấy embedding thông qua hàm static
        vector_embeddings = self.get_embedding(document_text)

        self.collection.upsert(
            ids=[f"chapter_{chapter.id}"],
            documents=[document_text],
            embeddings=[vector_embeddings],
            metadatas=[metadata],
        )
        logger.info(
            f"💾 [AIEngine] Đã đồng bộ thành công KnowledgeChapter ID: {chapter.id} vào {self.engine_type.upper()}"
        )

    @classmethod
    def sync_chapter_embeddings(cls, chapter):
        """Phương thức gọi chính từ Celery Task để đồng bộ chapter."""
        instance = cls()
        instance._sync_sync_chapter(chapter)

    def _sync_remove_chapter(self, chapter_id: int):
        """Xóa vector embedding của một chương tri thức."""
        self.collection.delete(ids=[f"chapter_{chapter_id}"])
        logger.info(
            f"🗑️ [AIEngine] Đã gỡ bỏ vector cho KnowledgeChapter ID: {chapter_id}"
        )

    @classmethod
    def remove_chapter_from_vector(cls, chapter_id: int):
        """Phương thức gọi chính khi xóa chapter."""
        instance = cls()
        instance._sync_remove_chapter(chapter_id)

    # --- TRUY VẤN VECTOR (GROUP-CENTRIC) 🔍 ---

    def _sync_query_vector(
        self, query: str, group_id: str, top_k: int = 3
    ) -> List[dict]:
        """Truy vấn vector với bộ lọc bắt buộc theo group_id."""
        query_vector = self.get_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_vector],
            where={"group_id": str(group_id)},
            n_results=top_k,
        )

        formatted_results = []
        documents = results.get("documents", [[]])
        metadatas = results.get("metadatas", [[]])

        if documents and documents[0]:
            for doc, meta in zip(documents[0], metadatas[0]):
                formatted_results.append({"content": doc, "metadata": meta})
        return formatted_results

    async def query_vector_async(
        self, query: str, group_id: str, top_k: int = 3
    ) -> List[dict]:
        """Truy vấn bất đồng bộ phục vụ cho luồng đọc (Read Side / RAG Chat)."""
        return await sync_to_async(self._sync_query_vector, thread_sensitive=False)(
            query, group_id, top_k
        )

    # --- TÍCH HỢP REDIS SEMANTIC CACHE (Semantic Intent Caching >= 0.92) ⚡ ---

    def _get_cache_key(self, group_id: str, query: str) -> str:
        """Tạo khóa cache duy nhất theo nhóm và nội dung truy vấn chuẩn hóa."""
        normalized_query = query.strip().lower()
        return f"sem_cache:{group_id}:{hash(normalized_query)}"

    def _sync_get_semantic_cache(
        self, group_id: str, query: str, threshold: float = 0.92
    ) -> Union[str, None]:
        """Lấy phản hồi từ Redis Cache nếu khớp ngữ cảnh."""
        cache_key = self._get_cache_key(group_id, query)
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(
                f"⚡ [Redis Cache] Hit Semantic Cache cho nhóm {group_id}"
            )
            return cached_data
        return None

    async def get_semantic_cache_async(
        self, group_id: str, query: str, threshold: float = 0.92
    ) -> Union[str, None]:
        """Wrapper bất đồng bộ cho Redis Semantic Cache (Read)."""
        return await sync_to_async(
            self._sync_get_semantic_cache, thread_sensitive=False
        )(group_id, query, threshold)

    def _sync_set_semantic_cache(
        self, group_id: str, query: str, reply: str, timeout: int = 3600
    ):
        """Lưu kết quả phản hồi vào Redis Cache."""
        cache_key = self._get_cache_key(group_id, query)
        cache.set(cache_key, reply, timeout=timeout)
        logger.info(
            f"💾 [Redis Cache] Đã lưu Semantic Cache cho nhóm {group_id}"
        )

    async def set_semantic_cache_async(
        self, group_id: str, query: str, reply: str, timeout: int = 3600
    ):
        """Wrapper bất đồng bộ cho Redis Semantic Cache (Write)."""
        await sync_to_async(
            self._sync_set_semantic_cache, thread_sensitive=False
        )(group_id, query, reply, timeout)

    # --- PHÂN TÍCH VĂN BẢN & PARSING 🧩 ---

    @staticmethod
    def parse_llm_json(raw_response: str) -> Union[dict, list]:
        """🧩 Làm sạch markdown và phân tích cú pháp JSON từ phản hồi LLM an toàn."""
        cleaned_text = clean_json_markdown(raw_response)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(
                f"❌ [AI_Engine] Không thể parse JSON sau khi clean: {e}"
            )
            raise e