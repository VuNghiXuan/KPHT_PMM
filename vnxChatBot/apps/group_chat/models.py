"""
Mục đích: Định nghĩa các thực thể cốt lõi cho Nhóm làm việc và Vòng đời tri thức.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.core.models (User)
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
import re
from django.utils.html import escape
from django.utils.safestring import mark_safe

User = get_user_model()

class ChatGroup(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên nhóm")
    plan_type = models.CharField(max_length=50, default="free", verbose_name="Gói dịch vụ")
    max_members = models.IntegerField(default=6, verbose_name="Số thành viên tối đa")
    is_active = models.BooleanField(default=True, verbose_name="Nhóm đang hoạt động")
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả nhóm")
    
    # ➕ Các trường phục vụ cấu hình AI riêng cho nhóm
    # ai_provider = models.CharField(max_length=50, default="gemini", verbose_name="Provider AI", choices=[('gemini', 'Gemini'), ('groq', 'Groq'), ('ollama', 'Ollama')])
    # ai_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Model AI đang dùng")
    # custom_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key riêng của nhóm")
    # is_admin_group = models.BooleanField(default=False, verbose_name="Là nhóm Admin hệ thống?", help_text="Nhóm này sẽ dùng chung cấu hình gốc từ LLMService")


    ai_provider = models.CharField(max_length=50, default="gemini", verbose_name="Provider AI", choices=[('gemini', 'Gemini'), ('groq', 'Groq'), ('ollama', 'Ollama')])
    ai_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Model AI đang dùng")
    custom_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key riêng của nhóm")
    is_admin_group = models.BooleanField(default=False, verbose_name="Là nhóm Admin hệ thống?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Nhóm chat"
        verbose_name_plural = "Danh sách nhóm chat"

    def __str__(self):
        return f"{self.name} ({self.plan_type})"
    

    # ➕ THÊM CÁC THUỘC TÍNH NÀY ĐỂ DÙNG TRONG TEMPLATE TUYỆT ĐỐI AN TOÀN
    @property
    def is_gemini(self):
        return self.ai_provider == 'gemini'

    @property
    def is_groq(self):
        return self.ai_provider == 'groq'

    @property
    def is_ollama(self):
        return self.ai_provider == 'ollama'
    
    @property
    def pending_knowledge_count(self):
        """Trả về số lượng đơn vị tri thức đang chờ duyệt."""
        return self.knowledge_units.filter(status='pending').count()

    @property
    def approved_knowledge_count(self):
        """Trả về số lượng đơn vị tri thức đã được duyệt vào RAG."""
        return self.knowledge_units.filter(status='approved').count()

class Membership(models.Model):
    """
    Quản lý thành viên trong nhóm.
    Tại sao (Why): Hỗ trợ AI thành viên (is_ai=True) mà không cần User ảo.
    Thay vì liên kết trực tiếp bảng Message với bảng User, kiến trúc chuẩn của vnxChatBot liên kết thông qua bảng trung gian Membership (sender=sender_membership). 
    Điều này giúp hệ thống dễ dàng quản lý quyền hạn của người dùng, phân biệt rõ vai trò thành viên hay tài khoản AI ảo trong từng ngữ cảnh nhóm cụ thể mà không cần tạo ra các User ảo trong hệ thống.
    """
    ROLE_CHOICES = [('admin', 'Admin'), ('member', 'Member')]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="memberships", verbose_name="Nhóm")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="memberships", verbose_name="Người dùng")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name="Vai trò")
    is_ai = models.BooleanField(default=False, verbose_name="Là AI?", help_text="Đánh dấu nếu đây là thành viên AI")

    class Meta:
        verbose_name = "Thành viên nhóm"
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username if self.user else 'AI'} - {self.group.name}"

class Document(models.Model):
    """
    Lưu trữ file gốc để trích xuất tri thức.
    """
    UPLOAD_TYPE_CHOICES = [('chat', 'Thảo luận'), ('auto', 'Tự động học')]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="documents", verbose_name="Nhóm chat")
    file = models.FileField(upload_to='media/groups/%Y/%m/%d/', verbose_name="Tệp tài liệu")
    # THÊM FIELD NÀY VÀO MODEL
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Người tải lên"
    )
    upload_type = models.CharField(max_length=10, choices=UPLOAD_TYPE_CHOICES, default='chat', verbose_name="Loại tải lên")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tải lên")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Ngày xử lý AI") # Field cần thiết cho luồng Signal

    class Meta:
        verbose_name = "Tài liệu"
        verbose_name_plural = "Tài liệu"

class KnowledgeUnit(models.Model):
    """
    Đơn vị kiến thức (RAG Source).
    """
    STATUS_CHOICES = [('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('rollback', 'Đã hủy')]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="knowledge_units", verbose_name="Tài liệu gốc")
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="knowledge_units", verbose_name="Nhóm")
    entity_name = models.CharField(max_length=100, verbose_name="Tên thực thể", help_text="VD: Vàng 610")
    context_tag = models.CharField(max_length=100, verbose_name="Ngữ cảnh", help_text="VD: Giao dịch")
    source_reference = models.CharField(max_length=255, verbose_name="Nguồn tham chiếu")
    content = models.TextField(verbose_name="Nội dung kiến thức")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Trạng thái duyệt")
    version = models.IntegerField(default=1, verbose_name="Phiên bản")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian duyệt")

    class Meta:
        verbose_name = "Đơn vị kiến thức"
        verbose_name_plural = "Đơn vị kiến thức"



class Message(models.Model):
    """
    [Class-level Docstring]: Quản lý toàn bộ thông tin tin nhắn trao đổi trong nhóm chat.
    Hỗ trợ tích hợp tin nhắn văn bản, trích dẫn, và đính kèm tài liệu (Document Attachment).
    """
    group = models.ForeignKey('ChatGroup', on_delete=models.CASCADE, related_name="messages", verbose_name="Nhóm")
    sender = models.ForeignKey('Membership', on_delete=models.CASCADE, verbose_name="Người gửi")
    content = models.TextField(verbose_name="Nội dung")
    
    # 📁 [DOCUMENT ATTACHMENT]: Liên kết trực tiếp tin nhắn với tài liệu tải lên (nếu có)
    document = models.ForeignKey(
        'Document', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='chat_messages',
        verbose_name="Tài liệu đính kèm",
        help_text="Liên kết đến tệp tài liệu nếu tin nhắn này là file upload"
    )
    
    reply_to = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='replies',
        verbose_name="Trả lời cho tin nhắn",
        help_text="Liên kết đến tin nhắn gốc nếu đây là tin nhắn reply"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")

    class Meta:
        verbose_name = "Tin nhắn"
        verbose_name_plural = "Tin nhắn"

    @property
    def sender_username(self):
        """
        [Architecture Thinking] Trả về tên người gửi một cách an toàn thông qua quan hệ Membership.
        Hỗ trợ phân biệt chính xác User thường và AI Assistant (is_ai=True).
        """
        if not self.sender:
            return "Thành viên ẩn danh"
        
        if getattr(self.sender, 'is_ai', False):
            return "AI Assistant"
        elif self.sender.user and hasattr(self.sender.user, 'username'):
            return self.sender.user.username
        return "Thành viên nhóm"

    @property
    def reply_sender_name(self):
        """
        [Architecture Thinking] Trả về tên người gửi của tin nhắn gốc một cách an toàn.
        Giải quyết triệt để vấn đề phân biệt User thường và AI Assistant (is_ai=True).
        """
        if not self.reply_to or not self.reply_to.sender:
            return "Thành viên"
        
        sender_membership = self.reply_to.sender
        if getattr(sender_membership, 'is_ai', False):
            return "AI Assistant"
        elif sender_membership.user and hasattr(sender_membership.user, 'username'):
            return sender_membership.user.username
        return "Thành viên nhóm"

    @property
    def short_formatted_content(self):
        """
        Trả về nội dung tin nhắn đã được format mention và cắt ngắn tối đa 80 ký tự 
        đảm bảo an toàn tuyệt đối cho khung trích dẫn (reply-quote-box).
        """
        if not self.content:
            return "[Nội dung trống]"
        
        # 1. Xử lý cắt ngắn chuỗi thô dưới 80 ký tự trước để tối ưu hiệu năng
        raw_text = str(self.content)
        if len(raw_text) > 80:
            raw_text = raw_text[:80] + "..."
            
        # 2. Escape chống XSS bảo mật tuyệt đối
        safe_truncated = escape(raw_text)
        
        # 3. Thay thế mention thành HTML badge chuẩn Bootstrap
        mention_regex = r'@([a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]+)'
        final_html = re.sub(
            mention_regex,
            r'<span class="badge bg-primary-subtle text-primary fw-bold px-1 rounded">@\1</span>',
            safe_truncated
        )
        
        # 4. Trả về định dạng Safe HTML (ĐÃ SỬA: Loại bỏ dấu phẩy thừa ở cuối lệnh return)
        return mark_safe(final_html)
    

class MessageFeedback(models.Model):
    """
    Feedback loop để tinh chỉnh AI (Fine-tuning Data).
    """
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


"""
Khi nhìn vào các trường (fields) được định nghĩa thực tế bên trong class `KnowledgeUnit`, bạn có nhận ra tại sao khi script test truyền tham số `title='Kien thuc kiem tra'` lại bị báo lỗi `TypeError: KnowledgeUnit() got unexpected keyword arguments: 'title'` không[cite: 2]? 

Theo cấu trúc model ở trên, trường nào dùng để lưu trữ tiêu đề hoặc tên gọi tương đương cho đơn vị kiến thức này?
"""