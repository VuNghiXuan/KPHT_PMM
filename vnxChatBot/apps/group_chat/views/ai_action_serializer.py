# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.group_chat.serializers import AIActionSerializer
from apps.group_chat.models import KnowledgeChapter

class AIRewriteAPIView(APIView):
    """
    API View tiếp nhận yêu cầu từ giao diện để gọi AI biên soạn lại nội dung tri thức.
    Tuân thủ quy tắc Group-Centric: cô lập dữ liệu theo group_id và chapter_id.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id, chapter_id):
        # 1. Validate dữ liệu đầu vào thông qua AIActionSerializer
        serializer = AIActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Lấy dữ liệu đã được làm sạch từ serializer
        user_prompt = serializer.validated_data['user_prompt']
        action_type = serializer.validated_data['action_type']

        try:
            # 3. Kiểm tra chương tri thức phải thuộc về nhóm hiện tại (Group-Centric Isolation)
            chapter = KnowledgeChapter.objects.get(id=chapter_id, group_id=group_id)
        except KnowledgeChapter.DoesNotExist:
            return Response(
                {"detail": "Không tìm thấy chương tri thức trong nhóm này."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. Giả lập kết quả trả về từ AI Engine
        rewritten_summary = f"[AI Biên soạn theo yêu cầu ({action_type}): '{user_prompt}']. Nội dung tóm tắt mới của chương {chapter.title}..."

        # 5. Phản hồi kết quả về client
        return Response({
            "status": "success",
            "chapter_id": str(chapter.id),
            "summary": rewritten_summary
        }, status=status.HTTP_200_OK)