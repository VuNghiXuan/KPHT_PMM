# -*- coding: utf-8 -*-
"""
File: apps/group_chat/views/conflict_chapter_listAPIView.py
Mục đích: Cung cấp các API endpoints quản lý danh sách xung đột và phê duyệt KnowledgeChapter theo nhóm (Group-Centric).
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter
from apps.group_chat.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

class ConflictChapterListAPIView(APIView):
    """API lấy danh sách các chương tri thức cần kiểm duyệt/xử lý trong nhóm."""
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id, format=None):
        group = get_object_or_404(ChatGroup, id=group_id)
        
        is_member = Membership.objects.filter(group=group, user=request.user).exists()
        if not is_member:
            return Response(
                {"detail": "🔒 Bạn không có quyền truy cập vào nhóm này."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 🚀 Lọc linh hoạt theo Query Parameter ?status= (VD: ?status=conflict_detected)
        status_param = request.GET.get('status')
        
        if status_param:
            chapters = KnowledgeChapter.objects.filter(
                group_id=group.id,
                status=status_param
            ).order_by("-updated_at")
        else:
            # Mặc định lọc tất cả các trạng thái cần kiểm duyệt/xử lý
            target_statuses = ['pending', 'staging', 'ready_to_approve', 'conflict_detected']
            chapters = KnowledgeChapter.objects.filter(
                group_id=group.id,
                status__in=target_statuses
            ).order_by("-updated_at")
        
        chapter_list = []
        for item in chapters:
            chapter_list.append({
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "status": item.status,  # 📌 Status giúp FE hiển thị badge tương ứng
                "has_conflict": item.has_conflict,
                "suggested_content": getattr(item, "suggested_content", ""),
                "reason": item.metadata.get("reason", "") if item.metadata else "",
                "conflict_with": item.metadata.get("conflict_with", []) if item.metadata else [],
                "updated_at": item.updated_at
            })
            
        return Response({
            "status": "success",
            "count": len(chapter_list),
            "conflicts": chapter_list  # Key 'conflicts' giữ tương thích với JS frontend
        }, status=status.HTTP_200_OK)

class KnowledgeChapterApprovalAPIView(APIView):
    """API View quản lý phê duyệt hoặc từ chối KnowledgeChapter."""
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id, chapter_id):
        group = get_object_or_404(ChatGroup, id=group_id)
        
        membership = Membership.objects.filter(group=group, user=request.user).exists()
        if not membership:
            return Response(
                {"status": "error", "message": "🔒 Bạn không có quyền truy cập nhóm này!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        chapter = get_object_or_404(KnowledgeChapter, id=chapter_id, group_id=group_id)
        action = request.data.get('action')

        if action not in ['approve', 'reject']:
            return Response(
                {"status": "error", "message": "⚠️ Hành động không hợp lệ. Chọn 'approve' hoặc 'reject'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = 'approved' if action == 'approve' else 'rollback'
        
        try:
            result = KnowledgeService.update_chapter_status(chapter.id, new_status, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"❌ Lỗi xử lý KnowledgeChapterApprovalAPIView: {str(e)}")
            return Response(
                {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )