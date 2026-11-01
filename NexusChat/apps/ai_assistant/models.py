"""
File: apps/ai_assistant/models.py
Mục đích: Quản lý tài liệu và cấu hình AI Provider cho từng nhóm.
"""
from django.db import models
from django.conf import settings
from apps.group_chat.models import ChatGroup

class AIConfig(models.Model):
    """
    Lưu trữ cấu hình AI (Provider, Key, Model) của người dùng hoặc nhóm.
    """
    PROVIDER_CHOICES = [
        ('groq', 'Groq'),
        ('gemini', 'Google Gemini'),
        ('ollama', 'Ollama'),
    ]
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='groq')
    api_key = models.CharField(max_length=255, verbose_name="API Key")
    model_name = models.CharField(max_length=100, verbose_name="Tên Model (ví dụ: llama-3.3-70b)")
    is_default = models.BooleanField(default=False, verbose_name="Sử dụng mặc định")

    class Meta:
        verbose_name = "Cấu hình AI"

class Document(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, verbose_name="Nhóm sở hữu")
    file = models.FileField(upload_to='ai_knowledge_base/%Y/%m/%d/', verbose_name="Tệp tài liệu")
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Tài liệu nhóm"