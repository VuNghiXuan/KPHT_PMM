# D:\ThanhVu\kpht\KPHT_PMM\vnxChatBot\config\asgi.py
"""
WSGI/ASGI config for config project.
"""

import os

# 1. Thiết lập biến môi trường trỏ đến settings trước tiên
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Khởi tạo ASGI application của Django để kích hoạt App Registry (tránh lỗi AppRegistryNotReady)
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# 3. Sau khi Django đã sẵn sàng, tiến hành import Channels và các routing liên quan
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.group_chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.group_chat.routing.websocket_urlpatterns
        )
    ),
})

# uvicorn config.asgi:application --reload --port 8000
