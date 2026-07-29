
"""
Module: group_chat.consumers
Author: Senior Software Engineer & Architecture Lead
Description: Xử lý giao tiếp WebSocket thời gian thực cho từng nhóm làm việc (ChatGroup Tenant). 
             Đóng vai trò điều phối tin nhắn giữa các thành viên và kích hoạt AI Listener.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.group_chat.models import ChatGroup, Membership, Message
from apps.ai_assistant.services.rag_engine import RAGEngine  # Engine RAG truy vấn tri thức nhóm

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Class: ChatConsumer
    Inherits: channels.generic.websocket.AsyncWebsocketConsumer
    
    Description: 
        Quản lý vòng đời kết nối WebSocket dựa trên định danh `group_id` (Tenant Isolation).
    """

    async def connect(self):
        """
        Thiết lập kết nối WebSocket, kiểm tra xác thực người dùng và phân quyền 
        truy cập vào ChatGroup cụ thể (Group-Centric Tenant).
        """
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f"chat_group_{self.group_id}"
        
        self.user = self.scope.get('user', AnonymousUser())
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close()
            return

        is_member = await self.check_user_membership(self.user, self.group_id)
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """
        Rời khỏi Channel Layer Group khi client ngắt kết nối WebSocket.
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Xử lý dữ liệu nhận từ Client, lưu tin nhắn User và kích hoạt AI RAG Engine.
        """
        try:
            data = json.loads(text_data)
            message_text = data.get("message", "").strip()
            
            if not message_text:
                return

            # 1. Lưu tin nhắn của User vào Database
            message_obj = await self.save_message(self.user, self.group_id, message_text)
            
            # 2. Broadcast tin nhắn của User tới nhóm
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_id": message_obj.id,
                    "sender_name": self.user.username,
                    "content": message_text,
                    "is_ai": False,
                }
            )

            # 3. Kích hoạt AI xử lý RAG phản hồi tự động
            await self.trigger_ai_response(message_text)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "error": "Invalid JSON payload format."
            }))

    async def chat_message(self, event):
        """
        Nhận sự kiện từ Channel Layer và đẩy dữ liệu JSON về client.
        """
        await self.send(text_data=json.dumps({
            'message_id': event.get('message_id'),
            'sender_name': event.get('sender_name', 'System'),
            'content': event.get('content', ''),
            'is_ai': event.get('is_ai', False),
        }))

    async def trigger_ai_response(self, user_query):
        """
        Khởi tạo RAGEngine gắn với `group_id` để truy vấn ChromaDB và gọi LLM.
        """
        rag_engine = RAGEngine(group_id=self.group_id)
        ai_reply_text = await rag_engine.query(query=user_query)

        ai_message_obj = await self.save_ai_message(self.group_id, ai_reply_text)

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
        """Kiểm tra quyền thành viên nhóm (Tenant Isolation)."""
        return Membership.objects.filter(user=user, group_id=group_id).exists()

    @database_sync_to_async
    def save_message(self, user, group_id, content):
        """
        Lưu tin nhắn của User vào Database, liên kết chặt chẽ với Tenant `group_id`.
        
        Args:
            user (User): Người gửi tin nhắn.
            group_id (int/str): Định danh nhóm làm việc.
            content (str): Nội dung tin nhắn.
        """
        group = ChatGroup.objects.get(id=group_id)
        sender_membership = Membership.objects.filter(group=group, user=user).first()
            
        return Message.objects.create(
            group=group,  
            sender=sender_membership,
            content=content
        )
    
    @database_sync_to_async
    def save_ai_message(self, group_id, content):
        """Lưu tin nhắn phản hồi từ AI với cờ nhận diện thành viên AI."""
        group = ChatGroup.objects.get(id=group_id)
        ai_membership = Membership.objects.filter(group=group, is_ai=True).first()
        return Message.objects.create(
            group=group,
            sender=ai_membership,
            content=content,
            # is_ai=True
        )


# python manage.py test_flow