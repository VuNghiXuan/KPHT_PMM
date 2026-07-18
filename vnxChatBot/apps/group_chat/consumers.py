"""
File: apps/group_chat/consumers.py
Mục đích: Xử lý giao tiếp WebSocket cho các nhóm chat.
Liên kết: apps.group_chat.models (Message), apps.ai_assistant.services (ai_service).
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatGroup, Message
from apps.ai_assistant.services import ai_service

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.group_name = f"chat_{self.group_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data['message']
        user = self.scope['user']

        # 1. Lưu tin nhắn vào DB
        msg = await self.save_message(user, self.group_id, message_content)

        # 2. Gửi tin nhắn tới tất cả thành viên trong nhóm
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': message_content, 'user': user.username}
        )

        # 3. Kích hoạt AI nếu có từ khóa "@AI"
        if "@AI" in message_content:
            await self.handle_ai_response(user, self.group_id, message_content)

    async def handle_ai_response(self, user, group_id, prompt):
        group = await database_sync_to_async(ChatGroup.objects.get)(id=group_id)
        
        # Gọi Service AI với tính năng RAG đã bật
        response = await database_sync_to_async(ai_service.generate_rag_response)(user, group, prompt)
        
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': response, 'user': 'AI Assistant'}
        )

    @database_sync_to_async
    def save_message(self, user, group_id, content):
        return Message.objects.create(user=user, group_id=group_id, content=content)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'message': event['message'], 'user': event['user']}))