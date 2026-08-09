# Module: ai_processor_service.py
# Path: apps/ai_assistant/services/ai_processor_service.py
# Description: Facade Service điều phối luồng xử lý AI, tích hợp AI_Engine và quản lý duyệt tri thức.
# Author: Kiến trúc sư VnxChatBot

import os
import logging
from django.utils import timezone
from django.conf import settings
from apps.group_chat.models import KnowledgeUnit
from apps.ai_assistant.vector_store import VectorDBManager
from apps.ai_assistant.engine import AI_Engine 
from apps.ai_assistant.services.notification import NotificationService
from apps.ai_assistant.services.document_processor import DocumentProcessorService

logger = logging.getLogger(__name__)

class AIProcessorService:
    
    @staticmethod
    def get_llm_config(chat_group):
        """
        Lấy cấu hình model từ ChatGroup với cơ chế fallback chuẩn hóa cho LiteLLM.
        """
        provider_map = {
            'gemini': 'gemini/gemini-1.5-flash',
            'groq': 'groq/llama3-70b-8192',
            'ollama': 'ollama/llama3'
        }
        
        model = chat_group.ai_model if chat_group.ai_model else provider_map.get(chat_group.ai_provider, 'gemini/gemini-1.5-flash')
        api_key = chat_group.custom_api_key if chat_group.custom_api_key else getattr(settings, f"{chat_group.ai_provider.upper()}_API_KEY", None)
        
        return model, api_key

    @staticmethod
    def process_document_knowledge(unit_id):
        """
        AI phân tích sâu tài liệu, sinh metadata, câu hỏi gợi ý và kiểm tra xung đột, 
        sau đó đưa về trạng thái PENDING để con người kiểm duyệt.
        """
        try:
            unit = KnowledgeUnit.objects.select_related('group', 'document').get(id=unit_id)
            chat_group = unit.group
            
            model_name, api_key = AIProcessorService.get_llm_config(chat_group)
            
            analysis_result = AI_Engine.deep_analyze_document(
                file_path=unit.document.file.path,
                model_name=model_name,
                api_key=api_key,
                existing_group_units=KnowledgeUnit.objects.filter(group=chat_group, status='approved')
            )
            
            unit.content = analysis_result.get('content', '')
            unit.suggested_queries = analysis_result.get('queries', [])
            unit.category = analysis_result.get('category', 'General')
            unit.conflict_notes = analysis_result.get('conflict_warning', None)
            
            unit.status = 'pending'
            unit.save()
            
            NotificationService.notify_admin(
                chat_group, 
                f"🧠 Tri thức mới chờ duyệt: {unit.entity_name} (Đã sinh {len(unit.suggested_queries)} câu hỏi gợi ý)"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error in deep analysis for KnowledgeUnit {unit_id}: {str(e)}")
            return False

    @staticmethod
    def sync_unit_to_vector(knowledge_unit):
        """Đẩy dữ liệu vào Vector DB thông qua DocumentProcessorService để đồng nhất luồng index."""
        DocumentProcessorService.commit_to_vector_db(knowledge_unit)

    @staticmethod
    def remove_unit_from_vector(knowledge_unit_id, group_id=None):
        """Xóa dữ liệu khỏi Vector DB khi Unit bị hủy/rollback, bảo đảm tuân thủ group_id."""
        vector_manager = VectorDBManager()
        vector_manager.delete_unit_embeddings(unit_id=knowledge_unit_id, group_id=group_id)

    @staticmethod
    def handle_manual_approval(unit_id):
        """
        Xử lý khi admin thực hiện duyệt thủ công một unit đang ở trạng thái 'pending'.
        """
        try:
            unit = KnowledgeUnit.objects.get(id=unit_id)
            unit.status = 'approved'
            unit.approved_at = timezone.now()
            unit.save()
            
            AIProcessorService.sync_unit_to_vector(unit)
            return True
        except KnowledgeUnit.DoesNotExist:
            return False