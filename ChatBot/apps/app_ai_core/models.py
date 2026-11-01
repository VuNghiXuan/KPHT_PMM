from django.db import models

class AIPromptConfig(models.Model):
    # 1. Định danh & Phân loại
    name = models.CharField("Tên gợi nhớ", max_length=100)
    module_code = models.CharField("Mã Module", max_length=50, db_index=True)
    function_code = models.CharField("Mã Chức năng", max_length=50, blank=True, null=True)
    is_default = models.BooleanField("Cấu hình mặc định", default=False)

    # 2. Nội dung AI
    system_prompt = models.TextField("System Prompt")
    temperature = models.FloatField("Độ sáng tạo (0.1 - 0.5)", default=0.2)

    # 3. Chiến lược LLM & Phần cứng
    PROVIDER_CHOICES = [
        ('AUTO', 'Tự động (Dựa trên Token Count)'),
        ('OLLAMA', 'Ép dùng Ollama (Local)'),
        ('GROQ', 'Ưu tiên Groq (Cloud)'),
        ('GEMINI', 'Ưu tiên Gemini (Cloud)'),
    ]
    provider_strategy = models.CharField("Chiến lược chọn AI", choices=PROVIDER_CHOICES, default='AUTO', max_length=20)
    model_name = models.CharField("Model cụ thể", max_length=100, blank=True, help_text="Ví dụ: qwen2.5:7b")
    
    # Các thông số kỹ thuật đẩy từ Gateway vào DB
    max_token_threshold = models.IntegerField("Ngưỡng chuyển đổi Token", default=6000)
    num_ctx = models.IntegerField("Context Window (Ollama)", default=8192)
    num_gpu_layers = models.IntegerField("GPU Layers (Ollama)", default=50, help_text="Số layer đẩy lên GPU, 0 là chạy CPU hoàn toàn")

    is_active = models.BooleanField("Đang kích hoạt", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cấu hình Prompt AI"
        verbose_name_plural = "Kho Prompt AI"
        unique_together = ('module_code', 'function_code')
        app_label = 'app_ai_core'

    def __str__(self):
        prefix = "[MẶC ĐỊNH] " if self.is_default else ""
        return f"{prefix}{self.module_code} | {self.function_code or 'GLOBAL'}"