from django.db import models
from apps.group_chat.models import ChatGroup

class GroupAIProvider(models.Model):
    """
    Mục đích: Quản lý cấu hình AI riêng biệt cho từng nhóm làm việc (Group-Centric).
    Tại sao: Cho phép mỗi nhóm linh hoạt lựa chọn nhà cung cấp LLM và cấu hình API Key riêng.
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
        help_text="Khóa bí mật do người dùng cung cấp riêng cho nhóm."
    )
    model_name = models.CharField(
        max_length=100, 
        default="gemini-2.0-flash", 
        verbose_name="Tên Model",
        help_text="Tên phiên bản model cụ thể (VD: qwen2.5:7b cho Ollama)."
    )

    class Meta:
        verbose_name = "Cấu hình AI nhóm"
        verbose_name_plural = "Cấu hình AI nhóm"

    @property
    def is_gemini(self) -> bool:
        return self.provider.lower() == 'gemini'

    @property
    def is_groq(self) -> bool:
        return self.provider.lower() == 'groq'

    @property
    def is_ollama(self) -> bool:
        return self.provider.lower() == 'ollama'

    # 💡 Tạo Alias property để tương thích ngược nếu code cũ gọi ai_model
    @property
    def ai_model(self) -> str:
        return self.model_name

    @ai_model.setter
    def ai_model(self, value: str):
        self.model_name = value

    def __str__(self):
        return f"AI Config cho nhóm {self.group.name} [{self.provider} - {self.model_name}]"