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
        Kiểm thử tự động cho luồng WebSocket real-time của ChatConsumer.
        Sử dụng TransactionTestCase để tương thích hoàn hảo với mọi cấu hình SQLite 
        mà không bị lỗi ImproperlyConfigured của ChannelsLiveServerTestCase.
    """

    async def asyncSetUp(self):
        """Thiết lập dữ liệu mẫu trước mỗi test case bất đồng bộ."""
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case WebSocket...")
        
        # 1. Tạo User thử nghiệm
        self.user = await database_sync_to_async(User.objects.create_user)(
            username='ws_test_user',
            email='wstest@vnx.com',
            password='password123'
        )
        print(f"👤 [SETUP]: Đã tạo user test: {self.user.username}")

        # 2. Tạo ChatGroup (Group-Centric Tenant)
        self.chat_group = await database_sync_to_async(ChatGroup.objects.create)(
            name='Phòng Chat Kiểm Thử WebSocket'
        )
        print(f"🏢 [SETUP]: Đã tạo ChatGroup: {self.chat_group.name} (ID: {self.chat_group.id})")

        # 3. Liên kết User vào Group qua Membership (Vai trò member)
        await database_sync_to_async(Membership.objects.create)(
            group=self.chat_group,
            user=self.user,
            role='member',
            is_ai=False
        )
        print("🔗 [SETUP]: Đã gán user vào nhóm qua Membership thành công.")

        # 4. Tạo thành viên AI ảo trong nhóm phục vụ kiểm thử
        await database_sync_to_async(Membership.objects.create)(
            group=self.chat_group,
            user=None,
            role='ai',
            is_ai=True
        )
        print("🤖 [SETUP]: Đã khởi tạo thành viên AI ảo trong nhóm.")

        # 5. Cấu hình ứng dụng Channels giả lập cho môi trường test
        self.application = ProtocolTypeRouter({
            "websocket": AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            ),
        })
        print("⚡ [SETUP]: Hoàn tất thiết lập môi trường giả lập Channels Router.")

    def setUp(self):
        """Bọc asyncSetUp để chạy mượt mà trong TransactionTestCase của Django."""
        super().setUp()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.asyncSetUp())

    async def test_websocket_connection_success_and_messaging(self):
        """
        Kiểm tra kịch bản: Thành viên hợp lệ kết nối thành công WebSocket, 
        gửi tin nhắn lên server và nhận lại bản tin broadcast (Real-time).
        """
        print("\n🧪 [TEST 1]: Bắt đầu kiểm tra kết nối WebSocket hợp lệ & gửi/nhận tin nhắn...")
        
        communicator = WebsocketCommunicator(
            self.application, 
            f"/ws/group/{self.chat_group.id}/"
        )
        communicator.scope['user'] = self.user

        print("🔌 [TEST 1]: Đang tiến hành kết nối WebSocket đến server...")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, "❌ Kết nối WebSocket thất bại đối với thành viên hợp lệ.")
        print("✅ [TEST 1]: Kết nối WebSocket thành công!")

        # Gửi tin nhắn chat thông thường từ Client lên server
        payload = {"message": "Xin chào hệ thống vnxChatBot!"}
        print(f"📤 [TEST 1]: Đang gửi payload: {payload}")
        await communicator.send_to(text_data=json.dumps(payload))

        # Nhận lại phản hồi broadcast từ Channel Layer Group
        print("⏳ [TEST 1]: Đang chờ nhận phản hồi broadcast từ Channel Layer...")
        response = await communicator.receive_from()
        data = json.loads(response)
        print(f"📥 [TEST 1]: Nhận được dữ liệu phản hồi: {data}")

        # Kiểm tra tính chính xác của dữ liệu phản hồi real-time
        self.assertEqual(data['content'], "Xin chào hệ thống vnxChatBot!")
        self.assertEqual(data['sender_name'], self.user.username)
        self.assertFalse(data['is_ai'])
        print("✔️ [TEST 1]: Kiểm tra nội dung tin nhắn broadcast thành công.")

        # Đóng kết nối
        print("🔒 [TEST 1]: Đang đóng kết nối WebSocket...")
        await communicator.disconnect()
        print("🎉 [TEST 1]: Hoàn tất kịch bản kiểm tra thành công.")

    async def test_websocket_connection_unauthorized_denied(self):
        """
        Kiểm tra kịch bản bảo mật Tenant Isolation: Người dùng không thuộc nhóm 
        hoặc chưa đăng nhập cố gắng kết nối WebSocket sẽ bị từ chối (tự động close).
        """
        print("\n🧪 [TEST 2]: Bắt đầu kiểm tra bảo mật (Tenant Isolation) với user ngoài nhóm...")
        
        outsider_user = await database_sync_to_async(User.objects.create_user)(
            username='outsider',
            password='password123'
        )
        print(f"👤 [TEST 2]: Đã tạo user ngoài nhóm: {outsider_user.username}")

        communicator = WebsocketCommunicator(
            self.application, 
            f"/ws/group/{self.chat_group.id}/"
        )
        communicator.scope['user'] = outsider_user

        print("🔌 [TEST 2]: Đang thử thiết lập kết nối WebSocket với quyền trái phép...")
        connected, subprotocol = await communicator.connect()
        
        self.assertFalse(connected, "❌ Lỗi bảo mật: User ngoài nhóm vẫn kết nối được WebSocket!")
        print("🛡️ [TEST 2]: Hệ thống đã từ chối kết nối trái phép thành công như kỳ vọng.")

        print("🔒 [TEST 2]: Đang đóng kết nối communicator...")
        await communicator.disconnect()
        print("🎉 [TEST 2]: Hoàn tất kịch bản kiểm tra bảo mật.")

    def test_run_async_cases(self):
        """Hàm helper đồng bộ để chạy các async test methods trong TransactionTestCase."""
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.test_websocket_connection_success_and_messaging())
        loop.run_until_complete(self.test_websocket_connection_unauthorized_denied())

# python manage.py test apps.group_chat.tests_chat_consumer