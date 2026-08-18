"""
File: apps/group_chat/services/conflict_service.py
Mục đích: Đóng gói toàn bộ logic xử lý mâu thuẫn tri thức (Human-in-the-Loop Conflict Resolution).
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services
"""

import logging
from django.db import transaction
from django.utils import timezone
from apps.group_chat.models import ConflictResolutionLog, KnowledgeUnit, KnowledgeChapter
from apps.ai_assistant.services import AIProcessorService
# Giả định import AI Engine chuẩn từ hệ thống ai_assistant
from apps.ai_assistant.services.ai_factory import AIFactory

logger = logging.getLogger(__name__)

class ConflictService:
    """
    Service quản lý và thực thi các hành động giải quyết xung đột tri thức 
    cho phân hệ Group-Centric.
    """

    @staticmethod
    @transaction.atomic
    def resolve_conflict(log_id: int, action: str, custom_content: str = None) -> ConflictResolutionLog:
        log = ConflictResolutionLog.objects.select_for_update().get(id=log_id)
        ku = log.knowledge_unit

        if action == 'overwrite':
            final_content = custom_content or getattr(log, 'proposed_content', None) or log.conflicting_content
            ku.content = final_content
            ku.status = 'approved'
            
            update_fields = ['content', 'status']
            if hasattr(ku, 'approved_at'):
                ku.approved_at = timezone.now()
                update_fields.append('approved_at')
                
            ku.save(update_fields=update_fields)

            log.status = 'resolved'
            log.resolved_at = timezone.now()
            log.save(update_fields=['status', 'resolved_at'])

            logger.info(f"✨ [ConflictResolver] Đã giải quyết xung đột log_id={log_id} bằng hình thức OVERWRITE.")

        elif action == 'discard':
            ku.status = 'rollback'
            ku.save(update_fields=['status'])

            log.status = 'discarded'
            log.resolved_at = timezone.now()
            log.save(update_fields=['status', 'resolved_at'])

            logger.info(f"🗑️ [ConflictResolver] Đã hủy bỏ xung đột log_id={log_id} bằng hình thức DISCARD.")
        else:
            raise ValueError(f"⚠️ Hành động không hợp lệ: {action}")

        return log

    @staticmethod
    def request_ai_rewrite(log_id: int, user_prompt: str) -> ConflictResolutionLog:
        """
        🤖 Kích hoạt AI viết lại hoặc hợp nhất nội dung dựa trên prompt hướng dẫn của người dùng.
        """
        log = ConflictResolutionLog.objects.get(id=log_id)
        
        # Gọi tầng AI Engine để xử lý tinh chỉnh nội dung dựa trên ngữ cảnh gốc và xung đột
        rewritten_text = AIProcessorService.rewrite_conflict_content(
            original=log.original_content,
            conflicting=log.conflicting_content,
            prompt=user_prompt
        )

        # Cập nhật kết quả đề xuất mới và chuyển trạng thái sang đang sửa đổi
        log.proposed_content = rewritten_text
        log.status = 'in_progress'
        log.save(update_fields=['proposed_content', 'status'])

        logger.info(f"🤖 [ConflictResolver] AI đã viết lại nội dung cho Conflict Log ID={log_id} thành công.")
        return log

    @staticmethod
    def resolve_by_overwrite(chapter: KnowledgeChapter) -> KnowledgeChapter:
        chapter.status = 'approved'
        chapter.save()
        return chapter

    @staticmethod
    def resolve_by_discard(chapter: KnowledgeChapter) -> KnowledgeChapter:
        chapter.status = 'rejected'
        chapter.save()
        return chapter

    @staticmethod
    @transaction.atomic
    def resolve_by_ai_rewrite(chapter: KnowledgeChapter, new_content: str) -> KnowledgeChapter:
        """
        Gọi AI Engine để tổng hợp, viết lại nội dung mâu thuẫn 
        giữa dữ liệu hiện tại trong chapter và nội dung mới đóng góp.
        """
        existing_content = getattr(chapter, 'content', None) or getattr(chapter, 'summary', '')
        
        prompt = f"""
        Bạn là Trợ lý Quản trị Tri thức thông minh (AI Data Auditor). 
        Nhiệm vụ của bạn là hợp nhất hai phiên bản nội dung tri thức sau đây thành một văn bản thống nhất, 
        mạch lạc, loại bỏ các thông tin mâu thuẫn nhưng vẫn giữ lại các chi tiết quan trọng nhất:

        --- NỘI DUNG HIỆN TẠI (APPROVED) ---
        {existing_content}

        --- NỘI DUNG MỚI ĐÓNG GÓP (PENDING/CONFLICT) ---
        {new_content}

        Hãy trả về kết quả là nội dung đã được viết lại hoàn chỉnh bằng tiếng Việt, cấu trúc rõ ràng, 
        không kèm theo các lời dẫn thừa thãi.
        """

        try:
            # Sử dụng AI_Engine chuẩn từ phân hệ ai_assistant thay vì get_default_engine
            from apps.ai_assistant.engine import AI_Engine
            ai_engine = AI_Engine()
            rewritten_content = ai_engine.generate_text(prompt=prompt) if hasattr(ai_engine, 'generate_text') else ai_engine._parse_llm_response(prompt)
            
            cleaned_content = rewritten_content.strip() if isinstance(rewritten_content, str) else str(new_content)
            if hasattr(chapter, 'summary'):
                chapter.summary = cleaned_content
            if hasattr(chapter, 'content'):
                chapter.content = cleaned_content
                
            chapter.status = 'approved'
            chapter.save()
            
            logger.info(f"AI Rewrite thành công cho KnowledgeChapter ID: {chapter.id} tại Group: {chapter.group_id}")
            return chapter

        except Exception as e:
            logger.error(f"Lỗi khi gọi AI Engine để viết lại chapter {chapter.id}: {str(e)}")
            raise RuntimeError(f"Không thể hoàn tất tiến trình AI Rewrite: {str(e)}")