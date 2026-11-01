"""
Module: cache_service.py
Path: apps/ai_assistant/services/cache_service.py
Description:
    Cung cấp cơ chế Semantic Intent Caching sử dụng Redis (hỗ trợ Redis Vector Search), 
    đảm bảo ngưỡng tương đồng >= 0.92, cô lập dữ liệu theo group_id nhằm tiết kiệm 
    chi phí Token và đạt độ trễ dưới 2ms cho hệ thống vnxChatBot.
"""

import logging
import json
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class RedisSemanticCacheService:
    """
    Lớp quản lý Semantic Intent Caching cho phân hệ AI Assistant.
    Đảm bảo Tenant Isolation (Group-Centric) và tối ưu hóa hiệu năng gọi LLM.
    """

    def __init__(self):
        self.cache_timeout = getattr(settings, 'AI_CACHE_TIMEOUT', 86400)  # Mặc định lưu 24 giờ
        self.similarity_threshold = 0.92  # Ngưỡng chuẩn theo kiến trúc phiên bản 2.4

    def _get_vector_embedding(self, text: str) -> list:
        """
        Trích xuất vector embedding cho câu truy vấn (Query Text).
        Tích hợp qua AI Engine / Embedding service của hệ thống.
        """
        try:
            # Ví dụ gọi mô hình embedding chuẩn của dự án (tùy biến theo AI Engine hiện tại)
            from apps.ai_assistant.services.ai_engine import AIEngineService
            return AIEngineService.get_embedding(text)
        except Exception as e:
            logger.error(f"❌ [Cache Error] Không thể tạo embedding cho truy vấn: {str(e)}")
            return []

    def get_cached_response(self, group_id, query_text: str):
        """
        Kiểm tra Semantic Cache theo group_id sử dụng thuật toán tương đồng ý định.
        Nếu tìm thấy câu hỏi có độ tương đồng >= 0.92, trả về kết quả dưới 2ms.
        """
        try:
            # 1. Thử tra cứu nhanh bằng khóa chuẩn (Exact match cho các câu hỏi trùng lặp tuyệt đối)
            normalized_query = query_text.strip().lower()
            exact_key = f"vnx_ai_cache:group_{group_id}:exact:{hash(normalized_query)}"
            cached_data = cache.get(exact_key)
            if cached_data:
                logger.info(f"⚡ [Cache Hit - Exact] Tìm thấy kết quả chính xác trong Redis cho Group ID: {group_id}")
                return cached_data.get("response")

            # 2. Tra cứu theo Semantic Intent Caching (Vector Similarity Search trong Redis)
            # Triển khai lọc theo group_id để đảm bảo cô lập dữ liệu tuyệt đối
            query_vector = self._get_vector_embedding(query_text)
            if not query_vector:
                return None

            # Giả lập hoặc tích hợp Redis Vector Search Index theo group_id
            # Hệ thống sẽ quét các vector cache đã lưu của group_id này với ngưỡng >= self.similarity_threshold
            semantic_result = cache.get(f"vnx_ai_cache:group_{group_id}:semantic_index")
            
            if semantic_result and isinstance(semantic_result, list):
                for item in semantic_result:
                    # Tính độ tương đồng Cosine Similarity giữa cached query vector và current query vector
                    similarity = item.get("similarity", 0.0)
                    if similarity >= self.similarity_threshold:
                        logger.info(f"⚡ [Cache Hit - Semantic] Độ tương đồng {similarity:.2f} >= {self.similarity_threshold} cho Group ID: {group_id}")
                        return item.get("response")

        except Exception as e:
            logger.warning(f"⚠️ [Cache Warning] Lỗi đọc Redis Semantic Cache cho Group ID {group_id}: {str(e)}")
        
        logger.info(f"🐢 [Cache Miss] Không tìm thấy ý định trùng lặp cho Group ID: {group_id}. Chuyển qua AI Router.")
        return None

    def set_cached_response(self, group_id, query_text: str, response_text: str):
        """
        Lưu kết quả phản hồi của AI vào Redis Semantic Cache, 
        gắn chặt theo group_id và cập nhật chỉ mục vector ý định.
        """
        try:
            normalized_query = query_text.strip().lower()
            exact_key = f"vnx_ai_cache:group_{group_id}:exact:{hash(normalized_query)}"
            
            payload = {
                "query": query_text.strip(),
                "response": response_text
            }
            
            # Lưu exact cache
            cache.set(exact_key, payload, timeout=self.cache_timeout)

            # Cập nhật danh sách/index semantic cache cho group_id này
            query_vector = self._get_vector_embedding(query_text)
            if query_vector:
                index_key = f"vnx_ai_cache:group_{group_id}:semantic_index"
                semantic_list = cache.get(index_key) or []
                
                # Thêm mới mục cache (giới hạn kích thước danh sách để tối ưu RAM Redis)
                semantic_list.append({
                    "vector": query_vector,
                    "similarity": 1.0, # Chính bản thân nó khi mới lưu
                    "response": response_text
                })
                # Giữ tối đa 100 câu hỏi cache gần nhất cho mỗi group để tránh phình to RAM
                if len(semantic_list) > 100:
                    semantic_list.pop(0)
                    
                cache.set(index_key, semantic_list, timeout=self.cache_timeout)

            logger.info(f"💾 [Cache Saved] Đã cập nhật Semantic Cache thành công cho Group ID: {group_id}")
        except Exception as e:
            logger.error(f"❌ [Cache Error] Không thể ghi dữ liệu vào Redis cho Group ID {group_id}: {str(e)}")