from django.db import models
from apps.group_chat.models import ChatGroup

class GroupAIProvider(models.Model):
    """
    Mục đích: Quản lý cấu hình AI riêng biệt cho từng nhóm làm việc (Group-Centric).
    Tại sao: Cho phép mỗi nhóm linh hoạt lựa chọn nhà cung cấp LLM và cấu hình API Key riêng 
    mà không ảnh hưởng đến các nhóm khác trong hệ thống Modular Monolith.
    Tác giả: Kiến trúc sư VnxChatBot
    """
    
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('groq', 'Groq'), 
        ('ollama', 'Ollama'),
        ('openai', 'OpenAI GPT')
    ]
    
    group = models.OneToOneField(
        ChatGroup, 
        on_delete=models.CASCADE, 
        related_name="ai_config", 
        verbose_name="Nhóm chat",
        help_text="Nhóm làm việc sở hữu cấu hình AI riêng biệt này."
    )
    provider = models.CharField(
        max_length=20, 
        choices=PROVIDER_CHOICES, 
        default='gemini', 
        verbose_name="Nhà cung cấp",
        help_text="Nhà cung cấp LLM mặc định là Google Gemini."
    )
    api_key = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="API Key", 
        help_text="Khóa bí mật do người dùng cung cấp riêng cho nhóm (bỏ trống nếu dùng chung hệ thống)."
    )
    model_name = models.CharField(
        max_length=100, 
        default="gemini-1.5-pro", 
        verbose_name="Tên Model",
        help_text="Tên phiên bản model cụ thể (mặc định cho Gemini)."
    )

    class Meta:
        verbose_name = "Cấu hình AI nhóm"
        verbose_name_plural = "Cấu hình AI nhóm"

    @property
    def is_gemini(self) -> bool:
        """Kiểm tra nhanh xem provider hiện tại có phải là Gemini không (giúp tránh so sánh chuỗi thô trong Template)."""
        return self.provider.lower() == 'gemini'

    @property
    def is_openai(self) -> bool:
        """Kiểm tra nhanh xem provider hiện tại có phải là OpenAI không."""
        return self.provider.lower() == 'openai'

    @property
    def is_groq(self) -> bool:
        """Kiểm tra nhanh xem provider hiện tại có phải là Groq không."""
        return self.provider.lower() == 'groq'

    @property
    def is_ollama(self) -> bool:
        """Kiểm tra nhanh xem provider hiện tại có phải là Ollama không."""
        return self.provider.lower() == 'ollama'

    def __str__(self):
        return f"AI Config cho nhóm {self.group.name} [{self.provider}]"