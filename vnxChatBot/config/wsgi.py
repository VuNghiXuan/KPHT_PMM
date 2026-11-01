"""
ASGI config for vnxChatBot project.
"""

import os
from django.core.asgi import get_asgi_application

# Thiết lập biến môi trường trỏ đến settings của dự án
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnxChatBot.settings')

# Khởi tạo ASGI application của Django HTTP trước
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.group_chat.routing as group_chat_routing # Hoặc đường dẫn routing websocket thực tế của bạn

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            group_chat_routing.routing.websocket_urlpatterns
        )
    ),
})

# uvicorn config.asgi:application --reload --host 127.0.0.1 --port 8000