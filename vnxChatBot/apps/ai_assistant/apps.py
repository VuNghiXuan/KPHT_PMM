"""
File: apps/ai_assistant/apps.py
Mô tả: Cấu hình App ai_assistant và kiểm tra kết nối Redis chủ động khi khởi động.
"""
import logging
import sys
from django.apps import AppConfig

logger = logging.getLogger(__name__)

class AiAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_assistant'
    verbose_name = '02. Trợ lý AI'

    def ready(self):
        # Đăng ký các tín hiệu (signals)
        import apps.ai_assistant.signals  # noqa

        # Kiểm tra kết nối Redis khi khởi động hệ thống
        from .utils import check_redis_status
        
        if not check_redis_status():
            msg = "⚠️ [CẢNH BÁO HỆ THỐNG - VnxChatBot]: Không thể kết nối tới Redis tại 127.0.0.1:6379. Vui lòng khởi động Docker/Redis để sử dụng WebSocket và tác vụ nền!"
            logger.warning(msg)
            print("\n" + "="*80 + f"\n{msg}\n" + "="*80 + "\n", file=sys.stderr)
        else:
            msg = "✅ [HỆ THỐNG - VnxChatBot]: Kết nối Redis thành công và sẵn sàng phục vụ RAG/WebSocket."
            logger.info(msg)
            print("\n" + "="*80 + f"\n{msg}\n" + "="*80 + "\n")