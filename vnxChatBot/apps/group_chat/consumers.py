"""
Module: group_chat.consumers
Author: Senior Software Engineer & Architecture Lead
Description: WebSocket Consumer đã tối ưu hóa, tích hợp AIEngineService chuẩn 
             và xử lý vòng đời kết nối an toàn theo mô hình Group-Centric.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from apps.group_chat.models import ChatGroup, Membership, Message
from apps.ai_assistant.services.ai_engine import AIEngineService

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f"chat_group_{self.group_id}"
        self.user = self.scope.get('user', AnonymousUser())
        
        # 1. Kiểm tra xác thực người dùng
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # 2. Kiểm tra tư cách thành viên và sự tồn tại của ChatGroup (Chống lỗi 403 khi nhóm bị xóa)
        is_member = await self.check_user_membership(self.user, self.group_id)
        if not is_member:
            logger.warning(f"[WebSocket 403] User '{self.user.username}' từ chối kết nối tới group_id={self.group_id} (Không tồn tại hoặc mất quyền).")
            await self.close(code=4003)
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

            # Lưu tin nhắn vào Database
            message_obj = await self.save_message(self.user, self.group_id, message_text, reply_to_id)
            
            # Xây dựng metadata cho reply
            reply_data = await self.get_reply_metadata(reply_to_id)

            # Broadcast tin nhắn ra toàn nhóm
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

            # AI Guardrail kích hoạt phản hồi tự động nếu thỏa mãn điều kiện
            if self.should_trigger_ai(message_text):
                await self.trigger_ai_response(message_text)

        except Exception as e:
            logger.error(f"[WebSocket Error] Receive fail: {str(e)}")

    async def chat_message(self, event):
        """Handler cho broadcast message qua channel layer."""
        await self.send(text_data=json.dumps(event))

    # --- HELPER METHODS (Dùng database_sync_to_async để tránh Blocking I/O) ---

    @database_sync_to_async
    def check_user_membership(self, user, group_id):
        """Kiểm tra xem ChatGroup có thực sự tồn tại và user có thuộc nhóm đó không."""
        try:
            chat_group = ChatGroup.objects.get(id=group_id)
            return Membership.objects.filter(user=user, group=chat_group).exists()
        except ChatGroup.DoesNotExist:
            return False

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
        # Sử dụng get_or_create hoặc kiểm tra an toàn để tránh lỗi Membership.DoesNotExist cho AI
        sender, created = Membership.objects.get_or_create(
            group=group, 
            is_ai=True,
            defaults={'user': None} # Tùy thuộc vào cấu trúc model Membership của bạn cho AI
        )
        return Message.objects.create(group=group, sender=sender, content=content)

    # --- AI INTEGRATION ---

    def should_trigger_ai(self, text):
        return any(k in text.lower() for k in ['ai ơi', '@ai', 'bot', 'trợ lý', 'tìm giúp']) or text.endswith('?')

    async def trigger_ai_response(self, user_query):
        try:
            # Khởi tạo AIEngineService chuẩn không tham số cấu trúc Model
            ai_engine = AIEngineService()
            current_group_id = str(self.group_id)
            
            # Sử dụng phương thức query_vector_async chuẩn xác từ AIEngineService
            vector_results = await ai_engine.query_vector_async(
                query=user_query, 
                group_id=current_group_id, 
                top_k=3
            )
            
            # Tổng hợp câu trả lời dựa trên kết quả truy xuất kho tri thức Vector DB
            if vector_results:
                contexts_list = []
                for res in vector_results:
                    if isinstance(res, dict):
                        contexts_list.append(res.get('content', str(res)))
                    else:
                        contexts_list.append(str(res))
                contexts = "\n".join(contexts_list)
                ai_reply = f"Dựa trên tài liệu đã duyệt của nhóm, tôi ghi nhận:\n{contexts}"
            else:
                ai_reply = "Xin lỗi, tôi chưa tìm thấy tài liệu hoặc thông tin phù hợp trong kho tri thức đã duyệt của nhóm."

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
            fallback_reply = "Hệ thống AI đang bận hoặc gặp sự cố kết nối tạm thời. Vui lòng thử lại sau."
            ai_msg = await self.save_ai_message(self.group_id, fallback_reply)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': ai_msg.id,
                    'sender_name': 'AI Assistant',
                    'content': fallback_reply,
                    'is_ai': True,
                    'created_at': ai_msg.created_at.strftime('%H:%M')
                }
            )