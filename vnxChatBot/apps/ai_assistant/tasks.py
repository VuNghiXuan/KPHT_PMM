# -*- coding: utf-8 -*-
# Path: apps/ai_assistant/tasks.py
# Description: Celery Tasks xử lý tài liệu bất đồng bộ (P1 Background), 
#               kiểm tra trùng lặp đa lớp và đồng bộ Vector Store theo group_id.
#               Tích hợp Rate Limiting, Exponential Backoff (chống lỗi 429) và Task Chaining.

import logging
import hashlib
from django.db import transaction
from celery import shared_task, chain

from apps.group_chat.models import KnowledgeChapter, RawDocument
from apps.group_chat.services.conflict_service import ConflictService
from apps.ai_assistant.services.document_processor import DocumentProcessorService
from apps.ai_assistant.vector_store import VectorDBManager
from apps.ai_assistant.models.text_choices import KnowledgeStatus
from apps.ai_assistant.models.groupAI import GroupAIProvider

logger = logging.getLogger(__name__)

# Khai báo ngoại lệ để kích hoạt Exponential Backoff tự động
TRY_RETRY_EXCEPTIONS = (Exception,)


@shared_task(
    bind=True, 
    queue='documents_p1_processing', 
    max_retries=5,
    rate_limit='10/m',  # Giới hạn tốc độ xử lý tối đa 10 tài liệu/phút để tránh nghẽn API
    autoretry_for=TRY_RETRY_EXCEPTIONS,
    retry_backoff=True,  # Tự động chờ theo cấp số nhân: 10s, 20s, 40s, 80s...
    retry_backoff_max=300,
    retry_jitter=True
)
def process_document_task(self, raw_document_id: int, group_id: int, user_id: int):
    """
    Task P1: Xử lý file tài liệu thô, phân rã thành các KnowledgeChapter nháp sử dụng
    Token Budget & Semantic Chunking, kiểm tra trùng lặp nội bộ và khởi chạy chuỗi (chain) P2.
    """
    try:
        logger.info(f"📚 [Celery P1] Bắt đầu phân tích file ID: {raw_document_id} cho nhóm: {group_id}")
        
        raw_doc = RawDocument.objects.get(id=raw_document_id, group_id=group_id)
        raw_doc.status = 'STAGING'
        raw_doc.save(update_fields=['status'])
        
        processing_result = DocumentProcessorService.process_and_index(raw_doc)
        
        if processing_result:
            # Tạo các chương nháp dựa trên Semantic Chunking & Token Budgeting
            chapters = DocumentProcessorService.create_draft_chapters_from_raw(raw_doc)
            seen_hashes = set()
            valid_chapters_for_p2 = []

            for chapter in chapters:
                if chapter.metadata is None:
                    chapter.metadata = {}

                # Tạo MD5 hash cho tiêu đề + tóm tắt
                chapter_text = f"{chapter.title}{chapter.summary}".strip().lower()
                content_hash = hashlib.md5(chapter_text.encode('utf-8')).hexdigest()

                # 🛠️ LỚP 1: Kiểm tra trùng lặp nội bộ ngay trong cùng file upload
                if content_hash in seen_hashes:
                    chapter.status = KnowledgeStatus.CONFLICT_DETECTED
                    chapter.has_conflict = True
                    chapter.metadata["reason"] = "Trùng lặp nội bộ ngay trong cùng tài liệu upload."
                    chapter.save()
                    continue

                seen_hashes.add(content_hash)

                # 🛠️ LỚP 2: Thu thập ngữ cảnh trùng tiêu đề trong cùng Group
                existing_chapters = KnowledgeChapter.objects.filter(
                    group_id=group_id,
                    title__iexact=chapter.title.strip()
                ).exclude(id=chapter.id)

                if existing_chapters.exists():
                    matched_ids = [str(c.id) for c in existing_chapters]
                    chapter.metadata["potential_conflicts"] = {
                        "reason": "Phát hiện trùng tiêu đề với các chương đã tồn tại trong nhóm.",
                        "matched_chapter_ids": matched_ids
                    }
                    chapter.save(update_fields=['metadata'])

                valid_chapters_for_p2.append(chapter)

            # 🛠️ LỚP 3: Sử dụng Task Chaining để kiểm tra trùng lặp ngữ nghĩa nối tiếp
            if valid_chapters_for_p2:
                task_chain = chain(
                    detect_semantic_overlap_task.s(chap.id) for chap in valid_chapters_for_p2
                )
                task_chain.apply_async()
                logger.info(f"🔗 [Celery P1] Đã kích hoạt Task Chain P2 cho {len(valid_chapters_for_p2)} chapters.")

            raw_doc.status = 'COMPLETED'
            raw_doc.save(update_fields=['status'])
            
            logger.info(f"✅ [Celery P1] Hoàn tất phân tích và sinh mục lục nháp cho RawDocument ID: {raw_document_id}")
            return {"status": "success", "raw_document_id": raw_document_id, "chapters_created": len(chapters)}
        else:
            logger.warning(f"⚠️ [Celery P1] Quá trình xử lý không thành công cho ID: {raw_document_id}")
            raw_doc.status = 'FAILED'
            raw_doc.save(update_fields=['status'])
            return {"status": "failed", "raw_document_id": raw_document_id}
            
    except RawDocument.DoesNotExist:
        logger.error(f"❌ [Celery P1 Security] Không tìm thấy tài liệu ID {raw_document_id} trong phạm vi nhóm {group_id}")
        return {"status": "not_found"}
        
    except Exception as exc:
        logger.error(f"❌ [Celery P1 Error] Lỗi khi xử lý task tài liệu ID {raw_document_id}: {str(exc)}")
        raise exc


@shared_task(
    bind=True, 
    max_retries=5,
    rate_limit='20/m',  # Giới hạn tốc độ gọi AI kiểm tra trùng lặp
    autoretry_for=TRY_RETRY_EXCEPTIONS,
    retry_backoff=True,  # Exponential Backoff tự động dừng và chờ tăng dần
    retry_backoff_max=300,
    retry_jitter=True
)
def detect_semantic_overlap_task(self, chapter_id: int):
    """
    Task P2: Đo độ tương đồng Cosine Similarity (threshold >= 0.85) với kho dữ liệu tri thức 
    đã được duyệt trong cùng group_id. Nếu phát hiện trùng lặp, dùng AI gợi ý biên soạn.
    """
    try:
        chapter = KnowledgeChapter.objects.get(id=chapter_id)
        chapter_text = f"{chapter.title} {chapter.summary}".strip()
        
        # Tính toán Embedding dựa trên Semantic Content
        content_embedding = VectorDBManager.compute_embedding(chapter_text)
        
        # 🛠️ Xử lý an toàn khi tìm kiếm trên VectorDB (Bắt buộc Metadata Filtering theo group_id)
        results = []
        try:
            results = VectorDBManager.search(
                embedding=content_embedding,
                group_id=chapter.group_id,
                limit=1,
                threshold=0.85
            )
        except Exception as search_err:
            logger.warning(f"⚠️ [Vector Search Warning] Không thể thực hiện truy vấn VectorDB (Collection có thể rỗng): {str(search_err)}")

        if chapter.metadata is None:
            chapter.metadata = {}

        if results:
            # 🤖 Lấy cấu hình AI riêng biệt của Nhóm (Group-Centric AI Provider)
            ai_config = GroupAIProvider.objects.filter(group_id=chapter.group_id).first()

            # Gọi ConflictService truyền kèm cấu hình AI của nhóm
            conflict_result = ConflictService.resolve_by_ai_rewrite(
                chapter=chapter,
                new_content=chapter.summary,
                ai_config=ai_config
            )
            
            merged_summary = conflict_result.get('merged_content') if isinstance(conflict_result, dict) else str(conflict_result)
            
            chapter.status = KnowledgeStatus.CONFLICT_DETECTED
            chapter.has_conflict = True
            chapter.suggested_content = merged_summary
            chapter.metadata.update({
                "conflict_with": [res.get('id') for res in results],
                "reason": "Phát hiện trùng lặp ngữ nghĩa cao với tri thức đã tồn tại trong nhóm.",
                "ai_rewrite_suggestion": merged_summary
            })
            chapter.save()
            
            logger.info(f"⚠️ [Conflict Detected]: Chapter {chapter_id} đã được tạo gợi ý biên soạn.")
        else:
            chapter.status = KnowledgeStatus.READY_TO_APPROVE
            chapter.has_conflict = False
            chapter.save(update_fields=['status', 'has_conflict', 'updated_at'])
            logger.info(f"✨ [Ready To Approve]: Chapter {chapter_id} đạt yêu cầu an toàn, sẵn sàng duyệt.")
            
        return {"status": "success", "chapter_id": chapter_id}

    except KnowledgeChapter.DoesNotExist:
        logger.error(f"❌ [Task Error]: Không tìm thấy KnowledgeChapter ID {chapter_id}")
        return {"status": "not_found", "chapter_id": chapter_id}
    except Exception as e:
        logger.error(f"❌ [Task System Error] Lỗi kiểm tra trùng lặp cho Chapter {chapter_id}: {str(e)}")
        raise e


@shared_task(
    bind=True, 
    max_retries=3,
    autoretry_for=TRY_RETRY_EXCEPTIONS,
    retry_backoff=True
)
def sync_chapter_to_vector_async(self, group_id_str: str, chapter_id: int):
    """
    Task P3: Đồng bộ KnowledgeChapter đã phê duyệt ('approved') vào VectorDB.
    Tuân thủ tuyệt đối QUY TẮC VÀNG: Chặn lưu dữ liệu chưa duyệt vào Vector Store.
    """
    try:
        chapter = KnowledgeChapter.objects.get(id=chapter_id)
        
        # 🛡️ KIỂM TRA QUY TẮC VÀNG: Chỉ phê duyệt mới được đưa vào VectorDB
        if chapter.status != KnowledgeStatus.APPROVED:
            logger.warning(f"⚠️ [Sync Aborted]: Chapter {chapter_id} chưa được phê duyệt (Status: {chapter.status}). Tiến hành gỡ bỏ khỏi Vector Store nếu tồn tại.")
            # Bảo đảm an toàn: Nếu từng chuyển từ approved -> pending/rejected, gỡ khỏi VectorDB ngay
            VectorDBManager.delete_unit_embeddings(unit_id=chapter.id, group_id=chapter.group_id)
            return f"Chapter {chapter_id} skipped: Not approved. Cleaned up if existed."

        success = DocumentProcessorService.commit_chapter_to_vector_db(chapter)
        
        if success:
            logger.info(f"✅ [Sync Success]: Chapter {chapter_id} (Group: {chapter.group_id}) đã được đồng bộ vào Vector Store.")
            return f"Chapter {chapter_id} synced successfully."
        else:
            logger.error(f"❌ [Sync Failed]: Không thể đẩy Chapter {chapter_id} vào Vector Store.")
            return f"Chapter {chapter_id} sync failed."

    except KnowledgeChapter.DoesNotExist:
        logger.error(f"❌ [Sync Error]: Không tìm thấy KnowledgeChapter ID {chapter_id} để đồng bộ.")
    except Exception as e:
        logger.error(f"❌ [Sync Error]: Lỗi hệ thống khi đồng bộ Chapter {chapter_id} vào VectorDB: {str(e)}")
        raise e