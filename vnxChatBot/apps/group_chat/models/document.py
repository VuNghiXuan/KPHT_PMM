from django.db import models
from django.conf import settings
from .group import ChatGroup

class Document(models.Model):
    UPLOAD_TYPE_CHOICES = [('chat', 'Thảo luận'), ('auto', 'Tự động học')]
    STATUS_CHOICES = [
        ('PENDING', 'Đang chờ xử lý'),
        ('STAGING', 'Đang phân tích cấu trúc'),
        ('APPROVED', 'Đã duyệt & Sync'),
        ('FAILED', 'Lỗi/Dữ liệu rác')
    ]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="documents", verbose_name="Nhóm chat")
    file = models.FileField(upload_to='media/groups/%Y/%m/%d/', verbose_name="Tệp tài liệu")
    original_filename = models.CharField(max_length=255, blank=True, null=True, verbose_name="Tên tệp gốc")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Người tải lên"
    )
    upload_type = models.CharField(max_length=10, choices=UPLOAD_TYPE_CHOICES, default='chat', verbose_name="Loại tải lên")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="Trạng thái xử lý")
    metadata = models.JSONField(default=dict, blank=True, help_text="Lưu thông tin layout, mục lục gợi ý từ AI Auditor.")
    
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tải lên")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Ngày xử lý AI")

    class Meta:
        verbose_name = "Tài liệu"
        verbose_name_plural = "Tài liệu"
        indexes = [models.Index(fields=['group', 'status'])]

    def get_file_name(self):
        return self.original_filename or self.file.name.split('/')[-1]


class RawDocument(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Đang chờ xử lý'),
        ('STAGING', 'Đang phân tích cấu trúc'),
        ('APPROVED', 'Đã duyệt & Sync'),
        ('FAILED', 'Lỗi/Dữ liệu rác')
    ]
    
    # 🔗 Sử dụng OneToOneField để khóa chặt tính duy nhất 1-1 với Document
    document = models.OneToOneField(
        Document, 
        on_delete=models.CASCADE, 
        related_name="raw_document", 
        verbose_name="Tài liệu gốc",
        null=True, 
        blank=True
    )
    group = models.ForeignKey(
        ChatGroup, 
        on_delete=models.CASCADE, 
        related_name="raw_documents",
        verbose_name="Nhóm chat"
    )
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_type = models.CharField(max_length=20, help_text="pdf, xlsx, docx, etc.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    raw_content = models.TextField(blank=True, null=True, verbose_name="Nội dung thô")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    metadata = models.JSONField(default=dict, help_text="Lưu thông tin layout, số trang, hash file.")

    class Meta:
        verbose_name = "Tài liệu thô"
        verbose_name_plural = "Tài liệu thô"
        indexes = [models.Index(fields=['group', 'status'])]