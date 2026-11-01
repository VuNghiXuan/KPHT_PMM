"""
Mục đích: Quản lý tin nhắn trao đổi nhóm và Feedback vòng lặp học tập.
Tác giả: Kiến trúc sư VnxChatBot
"""
import re
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.html import escape
from django.utils.safestring import mark_safe
from .group import ChatGroup, Membership
from .document import Document

User = get_user_model()

class Message(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages", verbose_name="Nhóm")
    sender = models.ForeignKey(Membership, on_delete=models.CASCADE, verbose_name="Người gửi")
    content = models.TextField(verbose_name="Nội dung")
    is_learned = models.BooleanField(default=False, verbose_name="Đã học tổng hợp tri thức")
    
    document = models.ForeignKey(
        Document, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='chat_messages',
        verbose_name="Tài liệu đính kèm"
    )
    reply_to = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='replies',
        verbose_name="Trả lời cho tin nhắn"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian gửi")
    
    class Meta:
        verbose_name = "Tin nhắn"
        verbose_name_plural = "Tin nhắn"

    @property
    def sender_username(self):
        if not self.sender:
            return "Thành viên ẩn danh"
        if getattr(self.sender, 'is_ai', False):
            return "AI Assistant"
        elif self.sender.user and hasattr(self.sender.user, 'username'):
            return self.sender.user.username
        return "Thành viên nhóm"

    @property
    def short_formatted_content(self):
        if not self.content:
            return "[Nội dung trống]"
        raw_text = str(self.content)
        if len(raw_text) > 80:
            raw_text = raw_text[:80] + "..."
        safe_truncated = escape(raw_text)
        mention_regex = r'@([a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]+)'
        final_html = re.sub(
            mention_regex,
            r'<span class="badge bg-primary-subtle text-primary fw-bold px-1 rounded">@\1</span>',
            safe_truncated
        )
        return mark_safe(final_html)


class MessageFeedback(models.Model):
    FEEDBACK_CHOICES = [('like', 'Thích'), ('dislike', 'Không thích')]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="feedbacks", verbose_name="Nhóm")
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="feedbacks", verbose_name="Tin nhắn")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người phản hồi")
    type = models.CharField(max_length=10, choices=FEEDBACK_CHOICES, verbose_name="Loại phản hồi")
    comment = models.TextField(null=True, blank=True, verbose_name="Góp ý chi tiết")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày phản hồi")

    class Meta:
        verbose_name = "Phản hồi AI"
        verbose_name_plural = "Phản hồi AI"