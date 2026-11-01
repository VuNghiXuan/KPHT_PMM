"""
Mục đích: Service trung tâm xử lý thông báo tới Admin nhóm.
Tác giả: Kiến trúc sư VnxChatBot
"""
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def notify_admin(group, message: str):
        """
        Gửi thông báo đến Admin của nhóm.
        Hiện tại: Log ra console.
        Tương lai: Tích hợp Telegram Bot hoặc WebSockets.
        """
        # Xác định Admin của nhóm
        admin_members = group.memberships.filter(role='admin')
        
        # Log thông báo cho hệ thống
        logger.info(f"[Notification - Group: {group.name}] {message}")
        
        # In ra console để Kiến trúc sư theo dõi trong quá trình dev
        print(f"--- [NOTIFY] Gửi đến Admin nhóm '{group.name}': {message} ---")
        
        # TODO: Triển khai logic gửi qua Telegram/WebSocket tại đây