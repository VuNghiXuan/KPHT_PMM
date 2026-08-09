"""
apps/ai_assistant/api_views.py

Nhiệm vụ: Điểm tiếp nhận request từ giao diện chat nhóm (group_id), kết hợp gọi qua Cache Service trước, nếu miss cache mới đẩy qua Router Service."""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.cache_service import RedisSemanticCacheService
from .services.router_service import MultiModelRouterService
from apps.group_chat.models import ChatGroup  # Giả định model Group

logger = logging.getLogger(__name__)

class AIChatView(APIView):
    """
    Điểm tiếp nhận yêu cầu chat nhóm. 
    Kiến trúc: Cache-Aside Pattern (Check Redis -> AI Router -> Update Redis).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache_service = RedisSemanticCacheService()
        self.router_service = MultiModelRouterService()

    def post(self, request, group_id):
        # 1. Xác thực quyền truy cập nhóm (Group-Centric Isolation)
        try:
            group = ChatGroup.objects.get(id=group_id)
        except ChatGroup.DoesNotExist:
            return Response({"error": "Nhóm không tồn tại"}, status=status.HTTP_404_NOT_FOUND)

        query = request.data.get("message")
        if not query:
            return Response({"error": "Message không được để trống"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Kiểm tra Cache (Semantic Cache)
        cached_response = self.cache_service.get_cached_response(group_id, query)
        if cached_response:
            logger.info(f"⚡ Hit Cache cho group {group_id}")
            return Response({"response": cached_response, "source": "cache"})

        # 3. Nếu Miss Cache: Gọi Router AI
        try:
            # Xác định độ phức tạp (Logic này có thể mở rộng dựa trên keyword hoặc độ dài)
            complexity = "complex" if len(query.split()) > 50 else "simple"
            
            # Gửi tin nhắn vào hệ thống Router
            ai_response, model_used = self.router_service.route_and_generate(
                messages=[{"role": "user", "content": query}],
                complexity=complexity
            )

            # 4. Lưu vào Cache cho các lần sau
            self.cache_service.set_cached_response(group_id, query, ai_response)

            return Response({
                "response": ai_response,
                "model": model_used,
                "source": "ai"
            })

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý AI cho group {group_id}: {str(e)}")
            return Response(
                {"error": "Hệ thống AI tạm thời gián đoạn."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )