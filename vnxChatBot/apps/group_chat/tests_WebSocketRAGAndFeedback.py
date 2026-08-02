"""
Module: group_chat.tests_WebSocketRAGAndFeedback
Author: Senior Software Engineer & Architecture Lead
Description: 
    Kiểm thử tích hợp tự động cho luồng:
    1. Kết nối WebSocket bảo mật theo nhóm (Tenant Isolation).
    2. Gửi tin nhắn qua WebSocket và kích hoạt RAGEngine phản hồi.
    3. Thực hiện thao tác Feedback Loop (Like/Dislike) qua API endpoint `knowledge_feedback_view`.
"""

import json
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
        Kiểm thử tích hợp luồng thời gian thực WebSocket kết hợp RAG và hệ thống Feedback.
    """
    
    # 💡 Cấu hình cho phép ChannelsLiveServerTestCase truy cập toàn bộ database vật lý trong môi trường test
    databases = '__all__'
    
    def setUp(self):
        """
        Khởi tạo dữ liệu mẫu trước mỗi kịch bản test (Tenant, User, Membership, AI Member).
        """
        # 1. Tạo User kiểm thử
        self.user = User.objects.create_user(username='rag_test_user', password='securepassword123')
        
        # 2. Tạo ChatGroup (Tenant)
        self.group = ChatGroup.objects.create(name='Phòng Kiểm Thử RAG & Feedback')
        
        # 3. Gán User làm thành viên nhóm
        Membership.objects.create(user=self.user, group=self.group, role='member')
        
        # 4. Khởi tạo thành viên AI ảo trong nhóm (Theo đúng quy chuẩn vnxChatBot)
        self.ai_membership = Membership.objects.create(
            group=self.group, 
            is_ai=True, 
            role='member'
        )

    @patch('apps.ai_assistant.services.rag_engine.RAGEngine.query')
    async def test_websocket_rag_and_feedback_flow(self, mock_rag_query):
        """
        Test Case: Kiểm tra luồng gửi tin nhắn qua WS -> Nhận RAG Response -> Gửi Feedback (Like/Dislike).
        """
        # Giả lập kết quả trả về từ RAGEngine
        mock_rag_query.return_value = "Đây là câu trả lời thông minh được trích xuất từ VectorStore của nhóm."

        # --- BƯỚC 1: KẾT NỐI WEBSOCKET ---
        from channels.testing import WebsocketCommunicator
        from config.asgi import application

        path = f"/ws/group/{self.group.id}/"
        communicator = WebsocketCommunicator(application, path)
        
        # Gán scope user đã xác thực cho communicator
        communicator.scope['user'] = self.user

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, "🔌 Kết nối WebSocket thất bại!")

        # --- BƯỚC 2: GỬI TIN NHẮN TỪ USER QUA WEBSOCKET ---
        await communicator.send_json_to({
            "message": "Hướng dẫn sử dụng hệ thống RAG?"
        })

        # Nhận tin nhắn broadcast phản hồi từ User
        response_user = await communicator.receive_json_from()
        self.assertEqual(response_user['content'], "Hướng dẫn sử dụng hệ thống RAG?")
        self.assertFalse(response_user['is_ai'])

        # Nhận tin nhắn broadcast phản hồi tự động từ AI (trigger từ RAGEngine)
        response_ai = await communicator.receive_json_from()
        self.assertEqual(response_ai['content'], "Đây là câu trả lời thông minh được trích xuất từ VectorStore của nhóm.")
        self.assertTrue(response_ai['is_ai'])
        
        ai_message_id = response_ai['message_id']

        # Đóng kết nối WebSocket
        await communicator.disconnect()

        # --- BƯỚC 3: KIỂM TRA API FEEDBACK LOOP (LIKE/DISLIKE) ---
        from django.test import AsyncClient
        client = AsyncClient()
        
        # Đăng nhập user thông qua client async
        await database_sync_to_async(client.force_login)(self.user)

        feedback_url = reverse('group_chat:knowledge_feedback', kwargs={'message_id': ai_message_id})

        # Gửi request Dislike để kích hoạt cơ chế Fine-tuning / đánh dấu xem lại
        response = await client.post(
            feedback_url,
            data=json.dumps({"type": "dislike", "comment": "Câu trả lời chưa sát với tài liệu thực tế."}),
            content_type="application/json"
        )

        response_data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'success')

        # --- BƯỚC 4: XÁC THỰC DỮ LIỆU ĐÃ LƯU TRONG DATABASE ---
        feedback_exists = await database_sync_to_async(
            MessageFeedback.objects.filter(
                group=self.group,
                message_id=ai_message_id,
                user=self.user,
                type='dislike'
            ).exists
        )()
        self.assertTrue(feedback_exists, "❌ Bản ghi MessageFeedback chưa được lưu vào Database thành công!")

    # python manage.py test apps.group_chat.tests_WebSocketRAGAndFeedback