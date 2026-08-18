# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter

class ConflictChapterListAPIView(APIView):
    """
    API lấy danh sách các chương/tài liệu đang gặp xung đột (conflict_detected) 
    trong phạm vi nhóm chat (group_id).
    """
    def get(self, request, group_id, format=None):
        # 1. Kiểm tra nhóm tồn tại
        group = get_object_or_404(ChatGroup, id=group_id)
        
        # 2. Kiểm tra quyền thành viên trong nhóm thông qua model Membership chuẩn
        is_member = Membership.objects.filter(group=group, user=request.user).exists()
        if not is_member:
            return Response(
                {"detail": "Bạn không có quyền truy cập vào nhóm này."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 3. Lấy danh sách KnowledgeChapter có trạng thái conflict_detected của nhóm
        conflicts = KnowledgeChapter.objects.filter(
            group_id=group.id,
            status="conflict_detected"
        ).order_by("-updated_at")
        
        # 4. Serialize dữ liệu trả về
        conflict_list = []
        for item in conflicts:
            conflict_list.append({
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "suggested_content": item.suggested_content,
                "reason": item.metadata.get("reason", ""),
                "conflict_with": item.metadata.get("conflict_with", []),
                "updated_at": item.updated_at
            })
            
        return Response({
            "status": "success",
            "count": len(conflict_list),
            "conflicts": conflict_list
        }, status=status.HTTP_200_OK)