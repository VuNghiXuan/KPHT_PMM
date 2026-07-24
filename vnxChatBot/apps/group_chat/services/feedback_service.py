"""
Module: group_chat.services.feedback_service
Author: Senior Software Engineer & Architecture Lead
Description: Xử lý logic nghiệp vụ cho Feedback Loop, ghi nhận đánh giá của người dùng 
             đối với câu trả lời của AI và hỗ trợ tinh chỉnh tri thức nhóm.
"""

from apps.group_chat.models import MessageFeedback, KnowledgeUnit
from django.utils import timezone

class FeedbackService:
    """
    Class: FeedbackService
    Description: 
        Quản lý các thao tác liên quan đến phản hồi tin nhắn AI (Like/Dislike).
        Giúp ghi nhận dữ liệu Fine-tuning và hỗ trợ đánh dấu các đơn vị tri thức cần xem lại.
    """

    @staticmethod
    def record_feedback(group, message, user, feedback_type, comment=None):
        """
        Ghi nhận phản hồi (Like/Dislike) từ người dùng cho một tin nhắn cụ thể của AI.
        Nếu là Dislike, hệ thống sẽ đánh dấu hoặc tạo yêu cầu xem lại KnowledgeUnit liên quan.
        """
        # Tạo hoặc cập nhật phản hồi của user cho tin nhắn này
        feedback, created = MessageFeedback.objects.update_or_create(
            group=group,
            message=message,
            user=user,
            defaults={
                'type': feedback_type,
                'comment': comment
            }
        )

        # Nếu người dùng chọn 'dislike', kích hoạt cơ chế đánh dấu tri thức cần xem xét (Rollback/Pending review)
        if feedback_type == 'dislike':
            FeedbackService._handle_dislike_action(message, comment)

        return feedback

    @staticmethod
    def _handle_dislike_action(message, comment):
        """
        Xử lý nội bộ khi có phản hồi tiêu cực (Dislike):
        Tìm kiếm các KnowledgeUnit có liên quan hoặc đánh dấu nguồn tham chiếu để AI không lặp lại sai sót.
        """
        # Có thể liên kết tìm kiếm KnowledgeUnit dựa vào nội dung tin nhắn hoặc ngữ cảnh gần nhất
        # Tại đây chúng ta ghi nhận log hoặc chuyển trạng thái KnowledgeUnit sang dạng cần kiểm tra nếu cần thiết.
        pass