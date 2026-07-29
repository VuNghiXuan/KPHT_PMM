"""
Mục đích: Định nghĩa các thực thể cốt lõi cho Nhóm làm việc và Vòng đời tri thức.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.core.models (User)
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class ChatGroup(models.Model):
    """
    Đại diện cho một nhóm làm việc độc lập. 
    Tại sao (Why): Phân tách dữ liệu triệt để (Tenant Isolation) theo nhóm.
    """
    name = models.CharField(max_length=255, verbose_name="Tên nhóm")
    plan_type = models.CharField(max_length=50, default="free", verbose_name="Gói dịch vụ", help_text="Xác định giới hạn tính năng của nhóm")
    max_members = models.IntegerField(default=6, verbose_name="Số thành viên tối đa")
    is_active = models.BooleanField(default=True, verbose_name="Nhóm đang hoạt động")
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả nhóm")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Nhóm chat"
        verbose_name_plural = "Các nhóm chat"

    def __str__(self):
        return self.name

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
    Tin nhắn trong nhóm.
    """
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages", verbose_name="Nhóm")
    sender = models.ForeignKey(Membership, on_delete=models.CASCADE, verbose_name="Người gửi")
    content = models.TextField(verbose_name="Nội dung")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")

    class Meta:
        verbose_name = "Tin nhắn"
        verbose_name_plural = "Tin nhắn"

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