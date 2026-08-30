# -*- coding: utf-8 -*-
# Path: apps/ai_assistant/tasks.py

"""
Module: ai_assistant.tasks
Mục đích: Gom nhóm toàn bộ Celery Tasks xử lý tài liệu, kiểm tra mâu thuẫn ngữ nghĩa 
và đồng bộ Vector Store một cách thống nhất, chống trùng lặp.
"""

import logging
from django.db import transaction
from celery import shared_task

from apps.group_chat.models import KnowledgeChapter, RawDocument
from apps.group_chat.services.conflict_service import ConflictService
from apps.ai_assistant.services.document_processor import DocumentProcessorService
from apps.ai_assistant.vector_store import VectorDBManager

logger = logging.getLogger(__name__)


@shared_task(bind=True, queue='documents_p1_processing', max_retries=3)
def process_document_task(self, raw_document_id: int, group_id: int, user_id: int):
    """
    🔄 Task xử lý tài liệu thô bất đồng bộ (P1 Background).
    Thực hiện bóc tách, khởi tạo cấu trúc cây tri thức nháp (KnowledgeChapter) ở trạng thái pending,
    tuyệt đối không đưa vào Vector Store cho đến khi được phê duyệt (Approved).
    """
    try:
        logger.info(f"📚 [Celery P1] Bắt đầu phân tích file ID: {raw_document_id} cho nhóm: {group_id}")
        
        # 🛡️ Hard Scoping: Bắt buộc khớp cả ID tài liệu và group_id
        raw_doc = RawDocument.objects.get(id=raw_document_id, group_id=group_id)
        
        # Chuyển trạng thái sang STAGING để hệ thống ghi nhận tiến trình phân tích cấu trúc
        raw_doc.status = 'STAGING'
        raw_doc.save(update_fields=['status'])
        
        # 🚀 1. Thực thi trích xuất văn bản thô
        processing_result = DocumentProcessorService.process_and_index(raw_doc)
        
        if processing_result:
            # 🚀 2. Tự động sinh ra các KnowledgeChapter nháp (pending)
            chapters = DocumentProcessorService.create_draft_chapters_from_raw(raw_doc)
            
            # 🚀 3. Kích hoạt tiếp tác vụ kiểm tra mâu thuẫn cho từng chương vừa tạo
            for chapter in chapters:
                detect_semantic_overlap_task.delay(chapter.id)
                
            raw_doc.status = 'COMPLETED'
            raw_doc.save(update_fields=['status'])
            
            logger.info(f"✅ [Celery P1] Hoàn tất phân tích và sinh mục lục nháp cho RawDocument ID: {raw_document_id}")
            return {"status": "success", "raw_document_id": raw_document_id, "chapters_created": len(chapters)}
        else:
            logger.warning(f"⚠️ [Celery P1] Quá trình xử lý trả về kết quả không thành công cho ID: {raw_document_id}")
            raw_doc.status = 'FAILED'
            raw_doc.save(update_fields=['status'])
            return {"status": "failed", "raw_document_id": raw_document_id}
            
    except RawDocument.DoesNotExist:
        logger.error(f"❌ [Celery P1 Security] Không tìm thấy tài liệu ID {raw_document_id} trong phạm vi nhóm {group_id}")
        return {"status": "not_found"}
        
    except Exception as exc:
        logger.error(f"❌ [Celery P1 Error] Lỗi nghiêm trọng khi xử lý task tài liệu ID {raw_document_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
    
@shared_task(bind=True, max_retries=3)
def detect_semantic_overlap_task(self, chapter_id):
    """
    Tác vụ ngầm: Kiểm tra trùng lặp ngữ nghĩa trong phạm vi group_id.
    """
    try:
        with transaction.atomic():
            chapter = KnowledgeChapter.objects.select_for_update().get(id=chapter_id)
            chapter_text = f"{chapter.title} {chapter.summary}".strip()
            
            content_embedding = VectorDBManager.compute_embedding(chapter_text)
            results = VectorDBManager.search(
                embedding=content_embedding,
                group_id=chapter.group_id,
                limit=1,
                threshold=0.85
            )
            
            if results:
                # Gọi ConflictService nhận kết quả hợp nhất
                conflict_result = ConflictService.resolve_by_ai_rewrite(
                    chapter=chapter,
                    new_content=chapter.summary
                )
                
                chapter.status = 'conflict_detected'
                chapter.has_conflict = True
                
                # Trích xuất nội dung hợp nhất an toàn từ kết quả AI Rewrite
                merged_summary = conflict_result.get('merged_content') if isinstance(conflict_result, dict) else str(conflict_result)
                if hasattr(chapter, 'suggested_content'):
                    chapter.suggested_content = merged_summary
                
                chapter.metadata = {
                    "conflict_with": [res.get('id') for res in results],
                    "reason": "Phát hiện trùng lặp ngữ nghĩa cao.",
                    "ai_rewrite_suggestion": merged_summary
                }
                chapter.save()
                
                logger.info(f"⚠️ [Conflict Detected]: Chapter {chapter_id} đã có gợi ý biên soạn.")
            else:
                chapter.status = 'ready_to_approve'
                chapter.has_conflict = False
                chapter.save(update_fields=['status', 'has_conflict', 'updated_at'])
                
    except KnowledgeChapter.DoesNotExist:
        logger.error(f"❌ [Task Error]: Không tìm thấy KnowledgeChapter ID {chapter_id}")
    except Exception as e:
        logger.error(f"❌ [Task System Error]: {str(e)}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def sync_to_vector_store(self, chapter_id):
    """
    Tác vụ ngầm: Đồng bộ chương tri thức đã phê duyệt (Approved) vào Vector Store.
    Đảm bảo cô lập dữ liệu theo group_id (Hard Scoping).
    """
    try:
        chapter = KnowledgeChapter.objects.get(id=chapter_id)
        
        if chapter.status != 'approved':
            logger.warning(f"⚠️ [Sync Aborted]: Chapter {chapter_id} chưa được phê duyệt (Status: {chapter.status}). Bỏ qua đồng bộ.")
            return f"Chapter {chapter_id} skipped: Not approved."

        VectorDBManager.upsert_embedding(
            group_id=chapter.group_id,
            text=f"{chapter.title} {chapter.summary}",
            doc_id=chapter.id,
            unit_id=chapter.id
        )
        
        logger.info(f"✅ [Sync Success]: Chapter {chapter_id} (Group: {chapter.group_id}) đã được đồng bộ vào Vector Store.")
        return f"Chapter {chapter_id} synced successfully."

    except KnowledgeChapter.DoesNotExist:
        logger.error(f"❌ [Sync Error]: Không tìm thấy KnowledgeChapter ID {chapter_id} để đồng bộ.")
    except Exception as e:
        logger.error(f"❌ [Sync Error]: Lỗi hệ thống khi đồng bộ Chapter {chapter_id} vào VectorDB: {str(e)}")
        raise self.retry(exc=e, countdown=60)