# apps/ai_assistant/tasks.py
from celery import app as celery_app
from apps.group_chat.models import KnowledgeUnit
from apps.group_chat.models import KnowledgeUnit
from .services.document_processor import DocumentProcessorService

@celery_app.task  # Sử dụng decorator từ app đã cấu hình
def process_document_task(knowledge_unit_id):
    """
    Task ngầm xử lý tài liệu khi có file upload mới.
    """
    try:
        unit = KnowledgeUnit.objects.get(id=knowledge_unit_id)
        DocumentProcessorService.process_and_index(unit)
    except KnowledgeUnit.DoesNotExist:
        return "Unit không tồn tại"