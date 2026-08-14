from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, queue='documents_p1_processing')
def process_document_task(self, knowledge_unit_id: int):
    """
    Task xử lý tài liệu nặng bất đồng bộ, tách biệt hoàn toàn khỏi luồng P0 Realtime.
    """
    from apps.ai_assistant.models import KnowledgeUnit
    from apps.ai_assistant.services.document_processor import DocumentProcessorService

    try:
        logger.info(f"🔄 [Celery P1] Bắt đầu xử lý file cho KnowledgeUnit ID: {knowledge_unit_id}")
        unit = KnowledgeUnit.objects.get(id=knowledge_unit_id)
        
        # Thực thi trích xuất qua Docling/Marker ở background
        success = DocumentProcessorService.process_and_index(unit)
        return {"status": "success" if success else "failed", "unit_id": knowledge_unit_id}
    except Exception as exc:
        logger.error(f"❌ [Celery P1 Error] Lỗi xử lý task tài liệu: {str(exc)}")
        # Tự động retry sau 60 giây nếu lỗi hệ thống tạm thời
        raise self.retry(exc=exc, countdown=60, max_retries=3)

    