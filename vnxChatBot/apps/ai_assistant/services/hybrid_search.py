"""
Module: hybrid_search.py
Path: apps/ai_assistant/services/hybrid_search.py
Description:
    Thực hiện tìm kiếm kết hợp Sparse (BM25) và Dense Vector 
    thông qua thuật toán RRF (Reciprocal Rank Fusion) với Tenant Isolation.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class HybridSearchService:
    """
    Lớp quản lý Hybrid Search cho phân hệ AI Assistant, 
    hỗ trợ cô lập dữ liệu theo group_id.
    """
    def __init__(self, vector_store_client):
        self.vector_store = vector_store_client

    def search(self, group_id: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Bắt buộc áp dụng metadata filtering để cô lập dữ liệu theo nhóm
        metadata_filter = {"group_id": str(group_id)}
        
        # 1. Dense Vector Search qua VectorDB
        dense_results = self._dense_search(query_text, metadata_filter, top_k)
        
        # 2. Sparse Search (BM25)
        sparse_results = self._sparse_search(query_text, metadata_filter, top_k)
        
        # 3. Trộn kết quả bằng Reciprocal Rank Fusion (RRF)
        return self._rrf_fusion(dense_results, sparse_results, top_k)

    def _dense_search(self, query: str, filter_dict: dict, top_k: int) -> list:
        """Truy vấn vector embedding với điều kiện lọc metadata group_id thông qua AIEngineService."""
        logger.info(f"🧠 [Dense Search] Đang truy vấn VectorDB với filter: {filter_dict}")
        try:
            # Import AIEngineService bên trong hàm để tránh vòng lặp phụ thuộc (circular import) nếu có
            from apps.ai_assistant.services.ai_engine import AIEngineService
            
            # Sử dụng vector_store_client được inject hoặc khởi tạo trực tiếp AIEngineService
            ai_engine = AIEngineService()
            
            # Lấy group_id từ filter_dict (đảm bảo tuân thủ Tenant Isolation)
            group_id = filter_dict.get("group_id")
            if not group_id:
                logger.warning("⚠️ [Dense Search] Thiếu group_id trong metadata_filter!")
                return []

            # Gọi phương thức truy vấn đồng bộ sẵn có của AIEngineService
            raw_results = ai_engine._sync_query_vector(query=query, group_id=group_id, top_k=top_k)
            
            # Chuẩn hóa định dạng đầu ra cho khớp với cấu trúc RRF (đảm bảo có trường 'id' hoặc 'content')
            formatted_results = []
            for idx, item in enumerate(raw_results):
                content = item.get('content', '')
                metadata = item.get('metadata', {})
                doc_id = metadata.get('chapter_id') or f"doc_{idx}"
                
                formatted_results.append({
                    "id": str(doc_id),
                    "content": content,
                    "metadata": metadata
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ [Dense Search Error] Lỗi khi truy vấn vector store: {str(e)}")
            return []

    def _sparse_search(self, query: str, filter_dict: dict, top_k: int) -> list:
        """Truy vấn từ khóa BM25 trên phạm vi group_id đảm bảo cô lập dữ liệu tuyệt đối."""
        logger.info(f"🔤 [Sparse Search] Đang truy vấn BM25 cho từ khóa: {query} với filter: {filter_dict}")
        try:
            group_id = filter_dict.get("group_id")
            if not group_id:
                logger.warning("⚠️ [Sparse Search] Thiếu group_id trong metadata_filter!")
                return []

            # 1. Truy vấn lấy toàn bộ các tài liệu (chapters) thuộc về group_id từ Database hoặc Vector Store
            from apps.group_chat.models import KnowledgeChapter
            chapters = list(KnowledgeChapter.objects.filter(group_id=group_id, status='approved'))
            
            if not chapters:
                logger.info(f"ℹ️ [Sparse Search] Không tìm thấy KnowledgeChapter nào được duyệt cho group_id: {group_id}")
                return []

            # Chuẩn bị tập dữ liệu corpus cho BM25
            corpus_docs = []
            for ch in chapters:
                text_content = f"{ch.title}\n{ch.summary}"
                corpus_docs.append({
                    "id": str(ch.id),
                    "content": text_content,
                    "metadata": {
                        "group_id": str(ch.group_id),
                        "chapter_id": ch.id,
                        "title": ch.title
                    }
                })

            # 2. Tokenize corpus và query phục vụ thuật toán BM25
            tokenized_corpus = [doc["content"].lower().split() for doc in corpus_docs]
            tokenized_query = query.lower().split()

            if not tokenized_corpus or not tokenized_query:
                return []

            # 3. Khởi tạo và tính điểm BM25
            from rank_bm25 import BM25Okapi
            bm25 = BM25Okapi(tokenized_corpus)
            doc_scores = bm25.get_scores(tokenized_query)

            # 4. Sắp xếp và lấy top_k kết quả cao nhất
            scored_docs = list(zip(corpus_docs, doc_scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            formatted_results = []
            for doc, score in scored_docs[:top_k]:
                if score > 0:  # Chỉ lấy các tài liệu có khớp điểm từ khóa
                    formatted_results.append({
                        "id": doc["id"],
                        "content": doc["content"],
                        "metadata": doc["metadata"]
                    })

            logger.info(f"🔤 [Sparse Search] Tìm thấy {len(formatted_results)} kết quả phù hợp qua BM25.")
            return formatted_results

        except ImportError:
            logger.warning("⚠️ Thư viện 'rank_bm25' chưa được cài đặt. Bỏ qua Sparse Search.")
            return []
        except Exception as e:
            logger.error(f"❌ [Sparse Search Error] Lỗi khi thực hiện BM25: {str(e)}")
            return []

    def _rrf_fusion(self, dense_list: list, sparse_list: list, top_k: int, k: int = 60) -> list:
        """
        Thuật toán RRF tính điểm tổng hợp dựa trên thứ hạng: Score = 1 / (k + rank)
        """
        logger.info(f"⚖️ [RRF Fusion] Đang kết hợp kết quả với hằng số k={k}")
        
        rrf_scores = {}
        
        # Gộp điểm từ kết quả Dense Search
        for rank, doc in enumerate(dense_list, start=1):
            doc_id = doc.get("id") or hash(doc.get("content", ""))
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {"doc": doc, "score": 0.0}
            rrf_scores[doc_id]["score"] += 1.0 / (k + rank)
            
        # Gộp điểm từ kết quả Sparse (BM25) Search
        for rank, doc in enumerate(sparse_list, start=1):
            doc_id = doc.get("id") or hash(doc.get("content", ""))
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {"doc": doc, "score": 0.0}
            rrf_scores[doc_id]["score"] += 1.0 / (k + rank)
            
        # Sắp xếp lại danh sách tài liệu theo điểm RRF giảm dần
        sorted_docs = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
        
        # Trả về giới hạn top_k kết quả tốt nhất
        return [item["doc"] for item in sorted_docs[:top_k]]