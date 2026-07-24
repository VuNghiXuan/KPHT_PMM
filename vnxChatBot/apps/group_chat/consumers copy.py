"""
Module: group_chat.consumers
Author: Senior Software Engineer & Architecture Lead
Description: Xử lý giao tiếp WebSocket thời gian thực cho từng nhóm làm việc (ChatGroup Tenant). 
             Đóng vai trò điều phối tin nhắn giữa các thành viên và kích hoạt AI Listener lắng nghe.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.group_chat.models import ChatGroup, Membership, Message, MessageFeedback
from apps.ai_assistant.services.rag_engine import RAGEngine  # Engine RAG truy vấn tri thức nhóm
from apps.ai_assistant.services.ai_factory import AIFactory    # Factory gọi LLM đa provider


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Class: ChatConsumer
    Inherits: channels.generic.websocket.AsyncWebsocketConsumer
    Description: 
        Quản lý kết nối WebSocket theo từng `group_id` (Tenant). 
        Thực hiện lưu trữ tin nhắn vào Database, phát tán realtime tới các thành viên 
        và kích hoạt AI phản hồi nếu tin nhắn có chứa từ khóa gọi AI hoặc theo cơ chế chủ động.
    """

    async def connect(self):
        """
        Thiết lập kết nối WebSocket, kiểm tra quyền hạn thành viên thuộc ChatGroup.
        """
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f"chat_group_{self.group_id}"
        
        # Kiểm tra user đã đăng nhập chưa
        self.user = self.scope.get('user', AnonymousUser())
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close()
            return

        # Kiểm tra user có thuộc nhóm này không (Group-Centric Tenant)
        is_member = await self.check_user_membership(self.user, self.group_id)
        if not is_member:
            await self.close()
            return

        # Tham gia vào Channel Layer Group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """
        Rời khỏi Channel Layer Group khi client ngắt kết nối.
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Nhận dữ liệu dạng text/json từ client WebSocket (khi thành viên gửi tin nhắn mới).
        """
        try:
            content = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = content.get('message', '').strip()
        if not message_text:
            return

        # 1. Lưu tin nhắn của người dùng vào DB bất đồng bộ
        message_obj = await self.save_message(self.user, self.group_id, message_text, is_ai=False)

        # 2. Phát tán tin nhắn của người dùng đến tất cả client trong nhóm realtime
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message_obj.id,
                'sender_name': self.user.username,
                'content': message_text,
                'is_ai': False,
            }
        )

        # 3. AI Listener: Kích hoạt phản hồi tự động từ AI (AI-as-a-Team-Member)
        # Có thể kích hoạt khi chứa từ khóa '@ai' hoặc cấu hình phản hồi liên tục
        # if '@ai' in message_text.lower() or True:
        #     await self.trigger_ai_response(message_text)
        if '@ai' in message_text.lower():
            await self.trigger_ai_response(message_text)

    async def chat_message(self, event):
        """
        Gửi dữ liệu tin nhắn từ Channel Layer về lại client WebSocket dưới dạng JSON.
        """
        await self.send(text_data=json.dumps({
            'message_id': event['message_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'is_ai': event['is_ai'],
        }))

    async def trigger_ai_response(self, user_query):
        """
        Logic AI-as-a-Team-Member: 
        Sử dụng RAGEngine để truy vấn tri thức nội bộ và gọi LLM qua AIFactory để phản hồi.
        """
        # Khởi tạo RAGEngine và gọi phương thức sinh câu trả lời bám sát tri thức nhóm
        rag_engine = RAGEngine()
        ai_reply_text = await rag_engine.generate_rag_answer(group_id=self.group_id, query=user_query)

        # Lưu tin nhắn phản hồi của AI vào DB
        ai_message_obj = await self.save_ai_message(self.group_id, ai_reply_text)

        # Phát tán câu trả lời của AI xuống giao diện nhóm theo thời gian thực
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': ai_message_obj.id,
                'sender_name': 'AI Assistant',
                'content': ai_reply_text,
                'is_ai': True,
            }
        )

    @database_sync_to_async
    def check_user_membership(self, user, group_id):
        """Kiểm tra người dùng có phải thành viên hợp lệ của nhóm hay không (Tenant Isolation)."""
        return Membership.objects.filter(user=user, chat_group_id=group_id).exists()

    @database_sync_to_async
    def save_message(self, user, group_id, content, is_ai=False):
        """Lưu tin nhắn của User hoặc AI vào Database gắn với Tenant group_id."""
        group = ChatGroup.objects.get(id=group_id)
        
        if is_ai:
            sender_membership = Membership.objects.filter(chat_group=group, is_ai=True).first()
        else:
            sender_membership = Membership.objects.filter(chat_group=group, user=user).first()
            
        return Message.objects.create(
            chat_group=group,
            sender=sender_membership,
            content=content
        )
    
    @database_sync_to_async
    def save_ai_message(self, group_id, content):
        """Lưu tin nhắn phản hồi từ AI (được gán với thành viên AI trong nhóm)."""
        group = ChatGroup.objects.get(id=group_id)
        ai_membership = Membership.objects.filter(chat_group=group, is_ai=True).first()
        return Message.objects.create(
            chat_group=group,
            sender=ai_membership,
            content=content
        )