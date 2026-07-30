"""
File: apps/ai_assistant/apps.py
Mô tả: Cấu hình App ai_assistant và kiểm tra kết nối Redis chủ động khi khởi động.
Tác giả: Kiến trúc sư VnxChatBot
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
            msg = "[CANH BAO HE THONG - VnxChatBot]: Khong the ket noi toi Redis tai 127.0.0.1:6379. Vui long khoi dong Docker/Redis de su dung WebSocket va tac vu nen!"
            logger.warning(msg)
            # Sử dụng ký tự ASCII thuần túy thay vì emoji để tránh UnicodeEncodeError trên Windows cp1252
            print("\n" + "="*80 + f"\n[!] {msg}\n" + "="*80 + "\n", file=sys.stderr)
        else:
            msg = "[HE THONG - VnxChatBot]: Ket noi Redis thanh cong va san sang phuc vu RAG/WebSocket."
            logger.info(msg)
            print("\n" + "="*80 + f"\n[OK] {msg}\n" + "="*80 + "\n")