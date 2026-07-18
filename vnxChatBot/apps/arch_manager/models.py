"""
Mục đích: Lưu trữ sơ đồ kiến trúc, luồng nghiệp vụ và trạng thái hệ thống.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.db import models

class SystemBlueprint(models.Model):
    """
    Lưu trữ các phiên bản của bản đồ kiến trúc hệ thống.
    """
    version = models.CharField(max_length=20, unique=True, verbose_name="Phiên bản")
    description = models.TextField(verbose_name="Mô tả thay đổi")
    content = models.TextField(verbose_name="Nội dung blueprint (Markdown)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bản đồ kiến trúc"

    def __str__(self):
        return f"Blueprint v{self.version}"