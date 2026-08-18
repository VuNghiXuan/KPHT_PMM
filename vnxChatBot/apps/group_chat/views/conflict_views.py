# -*- coding: utf-8 -*-
"""
Module: apps.group_chat.views.conflict_views
Mục đích: API View xử lý các hành động mâu thuẫn tri thức (Conflict Resolution) cho từng group_id.
          Tuân thủ nguyên tắc cô lập hard-scoping group_id và chuẩn hóa 3 hành động cốt lõi.
"""

import logging
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.group_chat.models import KnowledgeChapter, ChatGroup
from apps.ai_assistant.tasks import sync_to_vector_store

logger = logging.getLogger(__name__)


class ConflictResolutionAPIView(APIView):
    """
    API View xử lý các hành động mâu thuẫn tri thức cho từng group_id.
    Hỗ trợ các hành động: 
    - update / overwrite: Ghi đè bằng nội dung mới, đồng bộ VectorDB.
    - merge / ai_rewrite: Hợp nhất dựa trên bản thảo gợi ý của AI hoặc nội dung tùy chỉnh.
    - ignore / discard: Bỏ qua / từ chối nội dung mới, giữ nguyên hệ thống cũ.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id, chapter_id):
        action = request.data.get("action")
        
        # 🔄 Hỗ trợ cả tập lệnh cũ và mới để đảm bảo tương thích ngược
        valid_actions = ["update", "merge", "ignore", "overwrite", "discard", "ai_rewrite"]

        if action not in valid_actions:
            return Response(
                {"error": f"Hành động không hợp lệ. Chỉ chấp nhận các hành động: {valid_actions}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 🔒 Cô lập hoàn toàn theo group_id (Hard Scoping)
            group = ChatGroup.objects.get(id=group_id)
            
            # Sử dụng group_id thay vì quan hệ cũ để khớp chính xác với model KnowledgeChapter 2.5
            chapter = KnowledgeChapter.objects.get(id=chapter_id, group_id=group.id)
            
            if chapter.status != 'conflict_detected':
                return Response(
                    {"error": "Chương kiến thức này hiện không ở trạng thái xung đột."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except ChatGroup.DoesNotExist:
            return Response({"error": "Không tìm thấy nhóm hoặc không có quyền truy cập."}, status=status.HTTP_404_NOT_FOUND)
        except KnowledgeChapter.DoesNotExist:
            return Response({"error": "Không tìm thấy chương kiến thức hoặc không thuộc nhóm này."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                # Khóa bản ghi chống tranh chấp đồng thời (Optimistic/Pessimistic Locking)
                chapter = KnowledgeChapter.objects.select_for_update().get(id=chapter_id)

                if action in ["update", "overwrite"]:
                    # Ghi đè: Chuyển sang approved và kích hoạt đồng bộ VectorDB ngầm
                    chapter.status = 'approved'
                    chapter.has_conflict = False
                    chapter.save(update_fields=['status', 'has_conflict', 'updated_at'])
                    
                    # 🚀 Đẩy vào hàng đợi Celery để sync Vector Store
                    sync_to_vector_store.delay(chapter.id)
                    message = "Đã ghi đè tri thức thành công và kích hoạt đồng bộ VectorDB."

                elif action in ["ignore", "discard"]:
                    # Bỏ qua / Hủy bỏ: Đánh dấu rejected hoặc xóa chapter mới
                    chapter.status = 'rejected'
                    chapter.has_conflict = False
                    chapter.save(update_fields=['status', 'has_conflict', 'updated_at'])
                    message = "Đã hủy bỏ nội dung xung đột, giữ nguyên tri thức cũ."

                elif action in ["merge", "ai_rewrite"]:
                    # Hợp nhất: Lấy nội dung tùy chỉnh từ request hoặc bản thảo AI gợi ý sẵn có (`suggested_content`)
                    custom_content = request.data.get("new_content") or request.data.get("custom_content")
                    
                    if custom_content:
                        chapter.summary = custom_content
                    elif chapter.suggested_content:
                        chapter.summary = chapter.suggested_content
                    
                    chapter.status = 'approved'
                    chapter.has_conflict = False
                    chapter.save(update_fields=['summary', 'status', 'has_conflict', 'updated_at'])
                    
                    # 🚀 Đồng bộ vào Vector Store
                    sync_to_vector_store.delay(chapter.id)
                    message = "Đã biên soạn, hợp nhất và phê duyệt tri thức thành công."

                logger.info(f"✨ [Conflict Resolved]: Nhóm {group_id} đã xử lý Chapter {chapter_id} với hành động '{action}'.")

                return Response({
                    "status": "success",
                    "message": message,
                    "chapter_id": str(chapter.id),
                    "current_status": chapter.status
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ [Conflict API Error]: Lỗi khi xử lý xung đột cho chapter {chapter_id} tại group {group_id}: {str(e)}")
            return Response({"error": f"Lỗi hệ thống khi xử lý xung đột: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)