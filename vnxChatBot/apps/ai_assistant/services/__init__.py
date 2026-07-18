# apps/ai_assistant/services/__init__.py
from .ai_processor_service import AIProcessorService
from .notification import NotificationService # Thêm dòng này

__all__ = ['AIProcessorService', 'NotificationService']