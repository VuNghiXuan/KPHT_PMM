"""
Module: group_chat.routing
Description: Định nghĩa WebSocket URL patterns cho tính năng chat realtime theo nhóm.
"""

from django.urls import re_path
from apps.group_chat import consumers

# websocket_urlpatterns = [
#     re_path(r'ws/groups/(?P<group_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
# ]

websocket_urlpatterns = [
    # Khớp chính xác với đường dẫn client đang gửi lên: ws/chat/<group_id>/
    re_path(r'^ws/groups/(?P<group_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]