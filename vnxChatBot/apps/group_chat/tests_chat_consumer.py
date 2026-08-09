# -*- coding: utf-8 -*-
"""
Mục đích: Viết Unit Test cho WebSocket & ChatConsumer trong phân hệ group_chat.
Kiểm tra: 
1. Xác thực bảo mật kết nối WebSocket (Tenant Isolation & Membership).
2. Luồng gửi và nhận tin nhắn thời gian thực qua Channel Layer.
Tác giả: Senior Software Engineer & Architecture Lead
Module liên kết: apps.group_chat.consumers, apps.group_chat.models
"""

import json
import asyncio
from django.test import TransactionTestCase
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership
from apps.group_chat.routing import websocket_urlpatterns

User = get_user_model()


class ChatConsumerWebSocketTestCase(TransactionTestCase):
    """
    Class: ChatConsumerWebSocketTestCase
    Inherits: django.test.TransactionTestCase
    
    Description: 
        Kiểm thử tự động cho luồng WebSocket real-time của ChatConsumer[cite: 1].
    """

    def setUp(self):
        """Thiết lập dữ liệu đồng bộ và khởi tạo event loop riêng cho môi trường test."""
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.asyncSetUp())

    def tearDown(self):
        """Dọn dẹp và đóng event loop an toàn để giải phóng hoàn toàn file database."""
        try:
            self.loop.run_until_complete(self.asyncTearDown())
        finally:
            self.loop.close()
            super().tearDown()

    async def asyncSetUp(self):
        """Thiết lập dữ liệu mẫu trước mỗi test case bất đồng bộ[cite: 1]."""
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case WebSocket...")
        
        self.user = await database_sync_to_async(User.objects.create_user)(
            username='ws_test_user',
            email='wstest@vnx.com',
            password='password123'
        )

        self.chat_group = await database_sync_to_async(ChatGroup.objects.create)(
            name='Phòng Chat Kiểm Thử WebSocket'
        )

        await database_sync_to_async(Membership.objects.create)(
            group=self.chat_group,
            user=self.user,
            role='member',
            is_ai=False
        )

        await database_sync_to_async(Membership.objects.create)(
            group=self.chat_group,
            user=None,
            role='ai',
            is_ai=True
        )

        self.application = ProtocolTypeRouter({
            "websocket": AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            ),
        })

    async def asyncTearDown(self):
        """Dọn dẹp tài nguyên bất đồng bộ nếu cần."""
        pass

    async def test_websocket_connection_success_and_messaging(self):
        """Kiểm tra kết nối thành công và gửi/nhận tin nhắn real-time[cite: 1]."""
        communicator = WebsocketCommunicator(
            self.application, 
            f"/ws/group/{self.chat_group.id}/"
        )
        communicator.scope['user'] = self.user

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        payload = {"message": "Xin chào hệ thống vnxChatBot!"}
        await communicator.send_to(text_data=json.dumps(payload))

        response = await communicator.receive_from(timeout=10)
        data = json.loads(response)

        self.assertEqual(data['content'], "Xin chào hệ thống vnxChatBot!")
        self.assertEqual(data['sender_name'], self.user.username)
        self.assertFalse(data['is_ai'])

        await communicator.disconnect()

    async def test_websocket_connection_unauthorized_denied(self):
        """Kiểm tra bảo mật Tenant Isolation cho user ngoài nhóm[cite: 1]."""
        outsider_user = await database_sync_to_async(User.objects.create_user)(
            username='outsider',
            password='password123'
        )

        communicator = WebsocketCommunicator(
            self.application, 
            f"/ws/group/{self.chat_group.id}/"
        )
        communicator.scope['user'] = outsider_user

        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        await communicator.disconnect()

    def test_run_async_cases(self):
        """Hàm helper chạy các async test methods trong TransactionTestCase[cite: 1]."""
        self.loop.run_until_complete(self.test_websocket_connection_success_and_messaging())
        self.loop.run_until_complete(self.test_websocket_connection_unauthorized_denied())