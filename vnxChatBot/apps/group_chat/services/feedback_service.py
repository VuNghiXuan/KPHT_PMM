from apps.group_chat.models import KnowledgeUnit
from ..models import MessageFeedback

class FeedbackService:
    @staticmethod
    def handle_feedback(unit_id, action):
        """
        Xử lý hành động Like/Dislike của người dùng.
        action: 'approve' (Like) hoặc 'rollback' (Dislike)
        """
        unit = KnowledgeUnit.objects.get(id=unit_id)
        
        if action == 'approve':
            unit.status = 'approved'
        elif action == 'rollback':
            unit.status = 'rollback'
            
        unit.save() # Signal sẽ tự động sync với Vector DB
        return unit
    @staticmethod
    def record_feedback(user, message_id, feedback_type, comment=None):
        """
        Ghi nhận phản hồi và có thể kích hoạt logic gợi ý sửa đổi cho KnowledgeUnit.
        """
        # Logic: 
        # 1. Lưu feedback vào DB
        # 2. Nếu là 'dislike', có thể kích hoạt một signal hoặc service 
        #    để mark KnowledgeUnit liên quan là 'cần kiểm tra lại'.
        
        from ..models import Message
        message = Message.objects.get(id=message_id)
        
        feedback, created = MessageFeedback.objects.update_or_create(
            user=user,
            message=message,
            defaults={'type': feedback_type, 'comment': comment, 'group': message.group}
        )
        return feedback