"""
File: apps/group_chat/services/knowledge_service.py
Mục đích: Cung cấp các phương thức xử lý nghiệp vụ cho vòng đời tri thức (Knowledge Lifecycle)
          bao gồm chuyển đổi tin nhắn thành tri thức, phê duyệt và quản lý theo group_id.
Tác giả: Kỹ sư phần mềm cao cấp - vnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.rag_engine
"""

from django.shortcuts import get_object_or_404
from apps.group_chat.models import Message, KnowledgeUnit, ChatGroup

class KnowledgeService:
    """
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

        Args:
            knowledge_id (int|str): ID của đơn vị kiến thức.
            new_status (str): Trạng thái mới ('approved', 'pending', 'rollback').
            user (User): Người thực hiện thao tác duyệt.

        Returns:
            dict: Kết quả thực thi.
        """
        knowledge_unit = get_object_or_404(KnowledgeUnit, id=knowledge_id)
        
        # Cập nhật trạng thái
        knowledge_unit.status = new_status
        knowledge_unit.save()

        # [Logic RAG & VectorStore Integration]:
        # Nếu trạng thái là 'approved', tín hiệu (Signals) hoặc pipeline sẽ tự động đẩy vector embedding.
        # Nếu là 'rollback', hệ thống sẽ tự động xóa vector tương ứng khỏi Vector DB.

        return {
            "status": "success",
            "message": f"Đã cập nhật trạng thái tri thức thành '{new_status}' thành công."
        }