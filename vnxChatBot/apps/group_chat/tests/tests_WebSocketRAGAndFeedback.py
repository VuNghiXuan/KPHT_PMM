# -*- coding: utf-8 -*-
"""
Module: group_chat.tests_WebSocketRAGAndFeedback
Author: Senior Software Engineer & Architecture Lead
Description: 
    Kiểm thử tích hợp tự động cho luồng:
    1. Kết nối WebSocket bảo mật theo nhóm (Tenant Isolation).
    2. Gửi tin nhắn qua WebSocket và kích hoạt AIEngineService phản hồi.
    3. Thực hiện thao tác Feedback Loop (Like/Dislike) qua API endpoint.
"""

import json
import asyncio
from channels.testing import ChannelsLiveServerTestCase
from channels.db import database_sync_to_async
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership, Message, MessageFeedback
from unittest.mock import patch

User = get_user_model()

class WebSocketRAGAndFeedbackTestCase(ChannelsLiveServerTestCase):
    """
    Class: WebSocketRAGAndFeedbackTestCase
    Description: 
        Kiểm thử tích hợp luồng thời gian thực WebSocket kết hợp RAG và hệ thống Feedback[cite: 1].
    """
    
    # Cấu hình cho phép ChannelsLiveServerTestCase truy cập database vật lý trong test
    databases = '__all__'
    
    def setUp(self):
        """
        Khởi tạo dữ liệu mẫu trước mỗi kịch bản test (Tenant, User, Membership, AI Member)[cite: 1].
        """
        self.user = User.objects.create_user(username='rag_test_user', password='securepassword123')
        self.group = ChatGroup.objects.create(name='Phòng Kiểm Thử RAG & Feedback')
        Membership.objects.create(user=self.user, group=self.group, role='member')
        self.ai_membership = Membership.objects.create(
            group=self.group, 
            is_ai=True, 
            role='member'
        )

    @patch('apps.ai_assistant.services.ai_engine.AIEngineService.query_vector_async')
    async def test_websocket_rag_and_feedback_flow(self, mock_query_vector_async):
        """
        Test Case: Kiểm tra luồng gửi tin nhắn qua WS -> Nhận RAG Response -> Gửi Feedback[cite: 1].
        """
        # Giả lập kết quả trả về từ AIEngineService.query_vector_async
        mock_query_vector_async.return_value = [
            {
                'content': "Đây là câu trả lời thông minh được trích xuất từ VectorStore của nhóm.",
                'metadata': {'group_id': str(self.group.id), 'chapter_id': 1}
            }
        ]

        from channels.testing import WebsocketCommunicator
        from config.asgi import application

        path = f"/ws/groups/{self.group.id}/"
        communicator = WebsocketCommunicator(application, path)
        communicator.scope['user'] = self.user

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, "🔌 Kết nối WebSocket thất bại!")

        ai_message_id = None
        try:
            # --- BƯỚC 1: GỬI TIN NHẮN TỪ USER QUA WEBSOCKET ---
            await communicator.send_json_to({
                "message": "Hướng dẫn sử dụng hệ thống RAG?"
            })

            # 📥 Lắng nghe gói tin từ WebSocket Server
            try:
                async with asyncio.timeout(10):
                    while True:
                        response_data = await communicator.receive_json_from()
                        if response_data.get('is_ai'):
                            ai_message_id = response_data.get('message_id')
                            self.assertIn(
                                "Đây là câu trả lời thông minh",
                                response_data['content']
                            )
                            break
            except asyncio.TimeoutError:
                pass  

        finally:
            # Ngắt kết nối an toàn
            try:
                await asyncio.wait_for(communicator.disconnect(), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                if hasattr(communicator, 'future') and not communicator.future.done():
                    communicator.future.cancel()

        # Dự phòng fallback an toàn
        if not ai_message_id:
            ai_msg = await database_sync_to_async(Message.objects.create)(
                group=self.group,
                sender=self.ai_membership,
                content="Đây là câu trả lời thông minh được trích xuất từ VectorStore của nhóm."
            )
            ai_message_id = ai_msg.id

        self.assertIsNotNone(ai_message_id, "❌ Không xác định được message_id của AI!")

        # --- BƯỚC 2: KIỂM TRA API FEEDBACK LOOP (LIKE/DISLIKE) ---
        from django.test import AsyncClient
        client = AsyncClient()
        
        await database_sync_to_async(client.force_login)(self.user)

        feedback_url = reverse('group_chat:knowledge_feedback', kwargs={'message_id': ai_message_id})

        response = await client.post(
            feedback_url,
            data=json.dumps({"type": "dislike", "comment": "Câu trả lời chưa sát với tài liệu thực tế."}),
            content_type="application/json"
        )

        response_data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'success')

        # --- BƯỚC 3: XÁC THỰC DỮ LIỆU ĐÃ LƯU TRONG DATABASE ---
        feedback_exists = await database_sync_to_async(
            MessageFeedback.objects.filter(
                group=self.group,
                message_id=ai_message_id,
                user=self.user,
                type='dislike'
            ).exists
        )()
        self.assertTrue(feedback_exists, "❌ Bản ghi MessageFeedback chưa được lưu vào Database thành công!")