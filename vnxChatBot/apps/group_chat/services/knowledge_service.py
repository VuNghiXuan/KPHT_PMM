"""
File: apps/group_chat/services/knowledge_service.py
Mục đích: Cung cấp các phương thức xử lý nghiệp vụ cho vòng đời tri thức (Knowledge Lifecycle)
          bao gồm chuyển đổi tin nhắn thành tri thức, phê duyệt và quản lý theo group_id.
Tác giả: Kỹ sư phần mềm cao cấp - vnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.rag_engine
"""
import os
from django.conf import settings
from django.shortcuts import get_object_or_404
from apps.group_chat.models import Message, KnowledgeUnit, ChatGroup, Document
from django.utils import timezone
from apps.ai_assistant.engine import AI_Engine
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

logger = logging.getLogger(__name__)

class KnowledgeService:
    """
    Mô tả: Cung cấp các phương thức tự động hóa quy trình trích xuất và tổng hợp tri thức từ nhóm chat.
    Lớp dịch vụ chịu trách nhiệm xử lý các thao tác liên quan đến Kho tri thức nhóm (Knowledge Base).
    Tuân thủ tuyệt đối nguyên tắc Group-Centric (phân lập dữ liệu theo group_id).
    """

    @staticmethod
    def promote_message_to_knowledge(message_id, user):
        """
        Chuyển đổi một tin nhắn thông thường thành một Đơn vị Kiến thức (KnowledgeUnit)
        với trạng thái 'pending' (chờ phê duyệt), gắn chặt với nhóm chứa tin nhắn đó.

        Args:
            message_id (int|str): ID định danh của tin nhắn cần chuyển hóa.
            user (User): Người dùng thực hiện thao tác đưa tin nhắn vào kho tri thức.

        Returns:
            dict: Kết quả trạng thái và thông báo phản hồi cho client.
        """
        # Lấy tin nhắn và kiểm tra tính hợp lệ theo Group-Centric
        message = get_object_or_404(Message, id=message_id)
        group = message.group

        # Kiểm tra xem tin nhắn này đã tồn tại trong kho tri thức của nhóm chưa để tránh trùng lặp
        existing_unit = KnowledgeUnit.objects.filter(group=group, source_message=message).first()
        if existing_unit:
            return {
                "status": "warning",
                "message": "Tin nhắn này đã tồn tại trong kho tri thức của nhóm từ trước!"
            }

        # Tạo mới một KnowledgeUnit ở trạng thái 'pending' theo đúng quy trình Vòng đời tri thức
        knowledge_unit = KnowledgeUnit.objects.create(
            group=group,
            source_message=message,
            content=message.content,
            status='pending',
            created_by=user
        )

        return {
            "status": "success",
            "message": f"Đã đưa tin nhắn của [{message.sender_name}] vào hàng đợi tri thức nhóm thành công!",
            "knowledge_id": knowledge_unit.id
        }


    @staticmethod
    def update_knowledge_status(knowledge_id, new_status, user):
        """
        Cập nhật trạng thái phê duyệt của đơn vị kiến thức (Approved/Rollback).
        Kích hoạt đồng bộ hóa dữ liệu sang Vector Store nếu được duyệt.
        """
        knowledge_unit = get_object_or_404(KnowledgeUnit, id=knowledge_id)
        
        # Cập nhật trạng thái
        knowledge_unit.status = new_status
        knowledge_unit.save()

        return {
            "status": "success",
            "message": f"Đã cập nhật trạng thái tri thức thành '{new_status}' thành công."
        }

    
    @staticmethod
    def synthesize_from_chat_group(chat_group, batch_size=20):
        """
        Lấy các tin nhắn chưa học (is_learned=False), sử dụng AI_Engine tổng hợp 
        và tạo KnowledgeUnit ở trạng thái 'pending'.
        """
        unlearned_messages = Message.objects.filter(
            group=chat_group, 
            is_learned=False
        ).order_by('created_at')[:batch_size]

        if not unlearned_messages.exists():
            return None

        conversation_text = "\n".join([
            f"- {msg.sender_username}: {msg.content}" for msg in unlearned_messages
        ])

        # Tạo file tạm thời chứa nội dung hội thoại để tương thích với signature extract_and_score(file_path)
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'documents', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        file_name = f"group_learning_{chat_group.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_relative_path = os.path.join('documents', 'temp', file_name)
        absolute_file_path = os.path.join(settings.MEDIA_ROOT, file_relative_path)

        with open(absolute_file_path, 'w', encoding='utf-8') as f:
            f.write(conversation_text)

        try:
            # Gọi AI_Engine với đúng tham số file_path và group
            extracted_data, confidence = AI_Engine.extract_and_score(
                file_path=absolute_file_path,
                group=chat_group
            )
        finally:
            # Dọn dẹp tệp tạm sau khi xử lý xong
            if os.path.exists(absolute_file_path):
                try:
                    os.remove(absolute_file_path)
                except Exception:
                    pass

        doc = Document.objects.create(
            group=chat_group,
            file=file_relative_path,
            upload_type='auto'
        )

        knowledge_unit = KnowledgeUnit.objects.create(
            document=doc,
            group=chat_group,
            entity_name=extracted_data.get("context_tag", f"Hội thoại nhóm {chat_group.name}"),
            context_tag="Group Learning Loop",
            source_reference=f"ChatGroup ID: {chat_group.id}",
            content=extracted_data.get("content", conversation_text),
            status='pending'
        )

        message_ids = [msg.id for msg in unlearned_messages]
        Message.objects.filter(id__in=message_ids).update(is_learned=True)

        return knowledge_unit
    
    @staticmethod
    def get_pending_chapters(group_id):
        """
        Lấy danh sách các chương mục tri thức (KnowledgeChapter) đang ở trạng thái chờ duyệt ('pending')
        hoặc đang phân tích ('staging') của một nhóm cụ thể.
        
        Args:
            group_id (int|str): ID của ChatGroup cần lấy dữ liệu.
            
        Returns:
            QuerySet: Danh sách các KnowledgeChapter thỏa mãn điều kiện.
        """
        from apps.group_chat.models import KnowledgeChapter
        return KnowledgeChapter.objects.filter(
            group_id=group_id,
            status__in=['pending', 'staging']
        ).order_by('-created_at')

    @staticmethod
    def update_chapter_status(chapter_id, new_status, user):
        """
        Cập nhật trạng thái phê duyệt cho KnowledgeChapter với cơ chế bắt lỗi chi tiết.
        """
        from apps.group_chat.models import KnowledgeChapter
        
        try:
            chapter = KnowledgeChapter.objects.get(id=chapter_id)
            
            chapter.status = new_status
            # Dùng try-except bao quanh save để bắt lỗi từ Signals (VectorDB, Celery, v.v.)
            chapter.save() 
            
            return {
                "status": "success",
                "message": f"Đã cập nhật trạng thái chương mục [{chapter.title}] thành '{new_status}' thành công.",
                "chapter_id": chapter.id
            }
            
        except ObjectDoesNotExist:
            logger.error(f"❌ [KnowledgeService] Không tìm thấy chapter với ID: {chapter_id}")
            raise Http404("Không tìm thấy chương tri thức yêu cầu.")
            
        except Exception as e:
            # GHI LOG CỰC KỲ QUAN TRỌNG ĐỂ BIẾT NGUYÊN NHÂN LỖI 500
            logger.exception(f"💥 [KnowledgeService] Lỗi khi save chapter {chapter_id}: {str(e)}")
            # Ném lại ngoại lệ để test case nhận diện được lỗi
            raise e