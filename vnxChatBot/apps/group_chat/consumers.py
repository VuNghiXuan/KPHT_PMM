"""
Module: group_chat.consumers
Author: Senior Software Engineer & Architecture Lead
Description: WebSocket Consumer đã tối ưu hóa, loại bỏ trùng lặp logic, 
             tích hợp AI Guardrail và xử lý reply_to an toàn.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from apps.group_chat.models import ChatGroup, Membership, Message
from apps.ai_assistant.services.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f"chat_group_{self.group_id}"
        self.user = self.scope.get('user', AnonymousUser())
        
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close()
            return

        if not await self.check_user_membership(self.user, self.group_id):
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"[WebSocket] Connected: User '{self.user.username}' joined {self.room_group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"[WebSocket] Disconnected: {self.room_group_name} (Code: {close_code})")

    async def receive(self, text_data):
        """Xử lý tập trung tin nhắn từ client."""
        try:
            data = json.loads(text_data)
            message_text = data.get("message", "").strip()
            reply_to_id = data.get("reply_to_id")
            
            if not message_text:
                return

            # Lưu vào DB
            message_obj = await self.save_message(self.user, self.group_id, message_text, reply_to_id)
            
            # Xây dựng metadata cho reply
            reply_data = await self.get_reply_metadata(reply_to_id)

            # Broadcast
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_id": message_obj.id,
                    "sender_name": self.user.username,
                    "content": message_text,
                    "is_ai": False,
                    "reply_to": reply_data,
                    "created_at": message_obj.created_at.strftime('%H:%M')
                }
            )

            # AI Guardrail
            if self.should_trigger_ai(message_text):
                await self.trigger_ai_response(message_text)

        except Exception as e:
            logger.error(f"[WebSocket Error] Receive fail: {str(e)}")

    async def chat_message(self, event):
        """Handler cho broadcast."""
        await self.send(text_data=json.dumps(event))

    # --- HELPER METHODS (Dùng database_sync_to_async để tránh Blocking I/O) ---

    @database_sync_to_async
    def check_user_membership(self, user, group_id):
        return Membership.objects.filter(user=user, group_id=group_id).exists()

    @database_sync_to_async
    def save_message(self, user, group_id, content, reply_to_id=None):
        group = ChatGroup.objects.get(id=group_id)
        sender = Membership.objects.get(group=group, user=user)
        reply_msg = Message.objects.filter(id=reply_to_id, group=group).first() if reply_to_id else None
        return Message.objects.create(group=group, sender=sender, content=content, reply_to=reply_msg)

    @database_sync_to_async
    def get_reply_metadata(self, reply_to_id):
        if not reply_to_id: return None
        try:
            msg = Message.objects.select_related('sender__user').get(id=reply_to_id, group_id=self.group_id)
            return {
                'id': msg.id,
                'sender_name': "AI Assistant" if getattr(msg.sender, 'is_ai', False) else msg.sender.user.username,
                'content': msg.content[:100]
            }
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def save_ai_message(self, group_id, content):
        group = ChatGroup.objects.get(id=group_id)
        sender = Membership.objects.get(group=group, is_ai=True)
        return Message.objects.create(group=group, sender=sender, content=content)

    # --- AI INTEGRATION ---

    def should_trigger_ai(self, text):
        return any(k in text.lower() for k in ['ai ơi', '@ai', 'bot', 'trợ lý', 'tìm giúp']) or text.endswith('?')

    async def trigger_ai_response(self, user_query):
        try:
            rag_engine = RAGEngine(group_id=self.group_id)
            ai_reply = await rag_engine.query(query=user_query)
            ai_msg = await self.save_ai_message(self.group_id, ai_reply)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': ai_msg.id,
                    'sender_name': 'AI Assistant',
                    'content': ai_reply,
                    'is_ai': True,
                    'created_at': ai_msg.created_at.strftime('%H:%M')
                }
            )
        except Exception as e:
            logger.error(f"[AI Error] {str(e)}")