"""
Module: cache_service.py
Path: apps/ai_assistant/services/cache_service.py
Description:
    Cung cấp cơ chế Semantic Cache sử dụng Redis, hỗ trợ cô lập dữ liệu theo group_id 
    nhằm tiết kiệm chi phí Token và giảm độ trễ (Latency) cho hệ thống vnxChatBot.
"""

import logging
import hashlib
import json
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class RedisSemanticCacheService:
    """
    Lớp quản lý Redis Cache cho phân hệ AI Assistant.
    Đảm bảo Tenant Isolation (Group-Centric) và tối ưu hóa hiệu năng gọi LLM.
    """

    def __init__(self):
        # Sử dụng default cache của Django hoặc kết nối trực tiếp qua Redis URL nếu cấu hình riêng
        self.cache_timeout = getattr(settings, 'AI_CACHE_TIMEOUT', 86400)  # Mặc định lưu 24 giờ
        self.similarity_threshold = 0.92  # Ngưỡng chuẩn theo kiến trúc

    def _generate_cache_key(self, group_id: int, query_text: str) -> str:
        """
        Tạo khóa (Key) định danh duy nhất, gắn chặt với group_id để chống rò rỉ dữ liệu giữa các nhóm.
        """
        normalized_query = query_text.strip().lower()
        query_hash = hashlib.md5(normalized_query.encode('utf-8')).hexdigest()
        return f"vnx_ai_cache:group_{group_id}:{query_hash}"

    def get_cached_response(self, group_id: int, query_text: str):
        """
        Kiểm tra cache theo group_id. 
        Nếu tìm thấy câu hỏi trùng khớp, trả về ngay lập tức (Hit Cache).
        """
        cache_key = self._generate_cache_key(group_id, query_text)
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"⚡ [Cache Hit] Tìm thấy kết quả trong Redis cho Group ID: {group_id}")
                return cached_data.get("response")
        except Exception as e:
            logger.warning(f"⚠️ [Cache Warning] Không thể đọc Redis cho Group ID {group_id}: {str(e)}")
        
        logger.info(f"🐢 [Cache Miss] Không tìm thấy cache cho Group ID: {group_id}. Chuyển qua AI Router.")
        return None

    def set_cached_response(self, group_id: int, query_text: str, response_text: str):
        """
        Lưu kết quả phản hồi của AI vào Redis gắn theo group_id với thời gian TTL cấu hình sẵn.
        """
        cache_key = self._generate_cache_key(group_id, query_text)
        payload = {
            "query": query_text.strip(),
            "response": response_text
        }
        try:
            cache.set(cache_key, payload, timeout=self.cache_timeout)
            logger.info(f"💾 [Cache Saved] Đã lưu cache thành công cho Group ID: {group_id}")
        except Exception as e:
            logger.error(f"❌ [Cache Error] Không thể ghi dữ liệu vào Redis cho Group ID {group_id}: {str(e)}")