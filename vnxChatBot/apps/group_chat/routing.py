"""
Module: group_chat.routing
Description: Định nghĩa WebSocket URL patterns cho tính năng chat realtime theo nhóm.
"""

from django.urls import re_path
from apps.group_chat import consumers

websocket_urlpatterns = [
    # Hỗ trợ cả hai dạng đường dẫn (có chữ 's' hoặc không) để tương thích tuyệt đối với test case và client
    re_path(r'^ws/groups?/(?P<group_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]