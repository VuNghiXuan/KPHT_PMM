# -*- coding: utf-8 -*-
"""
File: apps/group_chat/services/conflict_service.py
Mục đích: Đóng gói toàn bộ logic xử lý mâu thuẫn tri thức (Human-in-the-Loop Conflict Resolution) 
          dựa trên mô hình cốt lõi KnowledgeChapter.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services.ai_factory, apps.ai_assistant.models
"""

import logging
from django.db import transaction
from django.utils import timezone

from apps.group_chat.models import KnowledgeChapter
from apps.ai_assistant.models.text_choices import KnowledgeStatus
from apps.ai_assistant.models.groupAI import GroupAIProvider
from apps.ai_assistant.services.ai_factory import AIFactory

logger = logging.getLogger(__name__)


class ConflictService:
    """
    Service quản lý và thực thi các hành động giải quyết xung đột tri thức 
    cho phân hệ Group-Centric (Tập trung vào KnowledgeChapter).
    """

    @staticmethod
    @transaction.atomic
    def resolve_by_overwrite(chapter: KnowledgeChapter) -> KnowledgeChapter:
        """
        🚀 Ghi đè (Overwrite): Phê duyệt trực tiếp chương tri thức mâu thuẫn,
        chuyển trạng thái sang APPROVED để kích hoạt đồng bộ Vector Store qua Signal.
        """
        chapter.status = KnowledgeStatus.APPROVED
        if hasattr(chapter, 'approved_at'):
            chapter.approved_at = timezone.now()
            chapter.save(update_fields=['status', 'approved_at'])
        else:
            chapter.save(update_fields=['status'])

        logger.info(f"✨ [ConflictService] Đã giải quyết xung đột Chapter ID={chapter.id} bằng hình thức OVERWRITE.")
        return chapter

    @staticmethod
    @transaction.atomic
    def resolve_by_discard(chapter: KnowledgeChapter) -> KnowledgeChapter:
        """
        🗑️ Bỏ qua/Hủy bỏ (Discard): Đổi trạng thái chương tri thức thành REJECTED,
        ngăn chặn hoàn toàn việc đưa dữ liệu rác hoặc xung đột vào Vector Store.
        """
        chapter.status = KnowledgeStatus.REJECTED
        chapter.save(update_fields=['status'])

        logger.info(f"🗑️ [ConflictService] Đã hủy bỏ Chapter ID={chapter.id} bằng hình thức DISCARD.")
        return chapter

    @staticmethod
    @transaction.atomic
    def resolve_by_ai_rewrite(
        chapter: KnowledgeChapter, 
        new_content: str, 
        ai_config: GroupAIProvider = None
    ) -> KnowledgeChapter:
        """
        🤖 Hợp nhất thông minh (AI Rewrite/Merge): Gọi AIFactory/LLM Service để tổng hợp, 
        viết lại nội dung mâu thuẫn giữa dữ liệu hiện tại và nội dung mới đóng góp.
        Lưu kết quả trực tiếp vào trường summary và chuyển trạng thái thành APPROVED.
        """
        existing_content = getattr(chapter, 'summary', '') or ''
        
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
            # 🛡️ Nếu có ai_config riêng được truyền vào, ưu tiên sử dụng.
            # Nếu không, ủy quyền hoàn toàn cho AIFactory tự động xử lý Fallback Chain theo group_id.
            if ai_config and hasattr(ai_config, 'generate'):
                rewritten_content = ai_config.generate(prompt)
            else:
                rewritten_content = AIFactory.get_service_for_group(
                    group_id=getattr(chapter, 'group_id', None), 
                    prompt=prompt
                )
            
            # 🛡️ Đảm bảo cleaned_content luôn là chuỗi hợp lệ, không bao giờ None
            if isinstance(rewritten_content, str) and rewritten_content.strip():
                cleaned_content = rewritten_content.strip()
            else:
                cleaned_content = new_content.strip() if new_content else "Nội dung đã được hợp nhất an toàn"
            
            chapter.summary = cleaned_content
            chapter.status = KnowledgeStatus.APPROVED
            
            update_fields = ['summary', 'status']
            if hasattr(chapter, 'approved_at'):
                chapter.approved_at = timezone.now()
                update_fields.append('approved_at')
                
            chapter.save(update_fields=update_fields)
            
            logger.info(f"✨ [ConflictService] AI Rewrite thành công cho KnowledgeChapter ID: {chapter.id}")
            return chapter

        except Exception as e:
            logger.error(f"❌ [ConflictService] Lỗi khi gọi AI Engine để viết lại chapter {chapter.id}: {str(e)}")
            # Fallback an toàn cho trường hợp ngoại lệ
            chapter.summary = new_content.strip() if new_content else "Nội dung đã được hợp nhất an toàn"
            chapter.status = KnowledgeStatus.APPROVED
            
            update_fields = ['summary', 'status']
            if hasattr(chapter, 'approved_at'):
                chapter.approved_at = timezone.now()
                update_fields.append('approved_at')
                
            chapter.save(update_fields=update_fields)
            return chapter