"""
Mục đích: Quản lý cấu hình AI riêng biệt cho từng nhóm.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.db import models
from apps.group_chat.models import ChatGroup

class GroupAIProvider(models.Model):
    """
    Cấu hình Provider riêng cho từng nhóm (Group-Centric).
    Tại sao: Cho phép nhóm nâng cấp AI theo nhu cầu mà không ảnh hưởng nhóm khác.
    """
    PROVIDER_CHOICES = [('groq', 'Groq'), ('gemini', 'Gemini'), ('ollama', 'Ollama')]
    
    group = models.OneToOneField(ChatGroup, on_delete=models.CASCADE, related_name="ai_config", verbose_name="Nhóm chat")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='ollama', verbose_name="Nhà cung cấp")
    api_key = models.CharField(max_length=255, null=True, blank=True, verbose_name="API Key", help_text="Khóa bí mật do người dùng cung cấp")
    model_name = models.CharField(max_length=100, default="qwen2.5:7b", verbose_name="Tên Model")

    class Meta:
        verbose_name = "Cấu hình AI nhóm"
        verbose_name_plural = "Cấu hình AI nhóm"

    def __str__(self):
        return f"AI Config cho {self.group.name} - {self.provider}"