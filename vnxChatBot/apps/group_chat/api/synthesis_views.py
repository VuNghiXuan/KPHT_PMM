# apps/group_chat/api/synthesis_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.group_chat.models import KnowledgeChapter
from apps.ai_assistant.services.synthesis_service import synthesize_knowledge_conflict

class KnowledgeSynthesisView(APIView):
    """
    API Endpoint: Nhận Prompt bổ sung và tổng hợp tài liệu xung đột.
    """
    def post(self, request, chapter_id):
        user_prompt = request.data.get('user_prompt', '')
        
        # 1. Lấy thông tin tài liệu cần xử lý
        chapter = KnowledgeChapter.objects.get(id=chapter_id, status='conflict_detected')
        
        # 2. Truy xuất các tài liệu bị xung đột (dựa trên metadata conflict_with)
        conflict_ids = chapter.metadata.get('conflict_with', [])
        existing_chapters = KnowledgeChapter.objects.filter(id__in=conflict_ids)
        
        # 3. Gọi Service tổng hợp (Service này đóng gói logic gọi AI)
        synthesized_text = synthesize_knowledge_conflict(
            new_content=chapter.summary,
            existing_contents=[c.summary for c in existing_chapters],
            user_prompt=user_prompt
        )
        
        # 4. Trả về bản nháp đã tổng hợp cho UI
        return Response({"suggested_content": synthesized_text})