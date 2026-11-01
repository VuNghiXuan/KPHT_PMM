"""
Module: group_chat.services.feedback_service
Author: Senior Software Engineer & Architecture Lead
Description: Xử lý logic nghiệp vụ cho Feedback Loop, ghi nhận đánh giá của người dùng 
             đối với câu trả lời của AI và hỗ trợ tinh chỉnh tri thức nhóm.
"""

from apps.group_chat.models import MessageFeedback

class FeedbackService:
    """
    Class: FeedbackService
    Description: 
        Service xử lý các nghiệp vụ liên quan đến việc ghi nhận phản hồi (Like/Dislike/Heart) 
        của người dùng đối với tin nhắn AI và kích hoạt quy trình cập nhật tri thức.
    """
    
    @staticmethod
    def record_feedback(group, message, user, feedback_type, comment=None):
        """
        Mục đích: 
            Ghi nhận hoặc cập nhật phản hồi của người dùng trong nhóm cho một tin nhắn cụ thể.
            Sử dụng đúng các trường 'user' và 'type' theo định nghĩa thực tế của MessageFeedback.
        """
        # ⚙️ Cập nhật hoặc tạo mới phản hồi dựa trên tin nhắn và user
        feedback, created = MessageFeedback.objects.update_or_create(
            message=message,
            user=user,
            defaults={
                'group': group,
                'type': feedback_type,  # 💡 Sử dụng trường 'type' thay vì 'feedback_type'
                'comment': comment
            }
        )
        return feedback, created