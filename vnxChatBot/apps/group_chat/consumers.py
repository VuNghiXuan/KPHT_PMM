"""
Module: group_chat.consumers
Author: Senior Software Engineer & Architecture Lead
Description: Xử lý giao tiếp WebSocket thời gian thực cho từng nhóm làm việc (ChatGroup Tenant). 
             Đóng vai trò điều phối tin nhắn giữa các thành viên, tích hợp cơ chế 
             AI Guardrail thông minh và hệ thống Log giám sát chi tiết vòng đời kết nối.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.group_chat.models import ChatGroup, Membership, Message
from apps.ai_assistant.services.rag_engine import RAGEngine  # Engine RAG truy vấn tri thức nhóm

# Khởi tạo logger phục vụ giám sát và trace lỗi hệ thống
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Class: ChatConsumer
    Inherits: channels.generic.websocket.AsyncWebsocketConsumer
    
    Description: 
        Quản lý vòng đời kết nối WebSocket dựa trên định danh `group_id` (Tenant Isolation).
        Điều phối việc nhận tin nhắn từ User, lưu trữ DB, broadcast thời gian thực 
        và ứng dụng cơ chế thông minh để quyết định có kích hoạt AI RAG Engine hay không.
    """

    async def connect(self):
        """
        Thiết lập kết nối WebSocket, kiểm tra xác thực người dùng và phân quyền 
        truy cập vào ChatGroup cụ thể (Group-Centric Tenant).
        """
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f"chat_group_{self.group_id}"
        
        self.user = self.scope.get('user', AnonymousUser())
        
        # 🛡️ Kiểm tra xác thực user
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            logger.warning(f"[WebSocket] Từ chối kết nối: User ẩn danh hoặc chưa xác thực (Group ID: {self.group_id})")
            await self.close()
            return

        # 🛡️ Kiểm tra quyền thành viên (Tenant Isolation)
        is_member = await self.check_user_membership(self.user, self.group_id)
        if not is_member:
            logger.warning(f"[WebSocket] Từ chối kết nối: User '{self.user.username}' không thuộc nhóm {self.group_id}")
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        # logger.info(f"[WebSocket] Kết nối thành công: User '{self.user.username}' đã tham gia phòng {self.room_group_name}")
        # Sửa lại trong file apps/group_chat/consumers.py tại dòng 59:
        logger.info(f"[WebSocket] Connected successfully: User '{self.user.username}' joined room {self.room_group_name}")

    async def disconnect(self, close_code):
        """
        Rời khỏi Channel Layer Group khi client ngắt kết nối WebSocket.
        
        Args:
            close_code (int): Mã trạng thái ngắt kết nối từ WebSocket.
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"[WebSocket] Ngắt kết nối: User '{getattr(self.user, 'username', 'Unknown')}' rời khỏi {self.room_group_name} (Code: {close_code})")

    async def receive(self, text_data):
        """
        Xử lý dữ liệu nhận từ Client qua WebSocket, thực hiện:
        1. Giải mã JSON payload.
        2. Lưu tin nhắn của User vào Database (bất đồng bộ).
        3. Broadcast tin nhắn của User tới toàn bộ thành viên trong nhóm.
        4. Kiểm tra điều kiện (Guardrail): Chỉ kích hoạt AI RAG Engine khi người dùng 
           gọi tên AI trực tiếp (ví dụ: chứa từ khóa 'ai', '@ai') để tránh AI làm phiền chuyện phiếm.
        """
        try:
            data = json.loads(text_data)
            message_text = data.get("message", "").strip()
            
            if not message_text:
                logger.debug("[WebSocket] Nhận tin nhắn rỗng từ client, bỏ qua xử lý.")
                return

            logger.info(f"[WebSocket] Nhận tin nhắn từ '{self.user.username}' trong nhóm {self.group_id}: '{message_text[:50]}...'")

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

            # 3. Intelligent Guardrail: Kiểm tra xem có nên gọi AI hay không?
            if self.should_trigger_ai(message_text):
                logger.info(f"[AI Guardrail] Kích hoạt AI RAG Engine cho nhóm {self.group_id} dựa trên nội dung truy vấn.")
                await self.trigger_ai_response(message_text)
            else:
                logger.debug(f"[AI Guardrail] Bỏ qua AI (tin nhắn thông thường/chuyện phiếm) trong nhóm {self.group_id}.")

        except json.JSONDecodeError:
            logger.error(f"[WebSocket Error] Lỗi định dạng JSON payload từ client: {text_data}")
            await self.send(text_data=json.dumps({
                "error": "Invalid JSON payload format."
            }))

    def should_trigger_ai(self, text):
        """
        Phương thức kiểm tra thông minh (Guardrail) xem tin nhắn có cần AI can thiệp hay không.
        
        Args:
            text (str): Nội dung tin nhắn của người dùng.
            
        Returns:
            bool: True nếu cần gọi AI, ngược lại False (để thành viên tự trò chuyện với nhau).
        """
        text_lower = text.lower()
        
        # Các dấu hiệu cho thấy người dùng muốn gọi AI:
        ai_keywords = ['ai ơi', '@ai', 'bot', 'trợ lý', 'tìm giúp', 'tra cứu', 'tài liệu']
        
        has_keyword = any(keyword in text_lower for keyword in ai_keywords)
        is_question = text.endswith('?')
        
        return has_keyword or is_question

    async def chat_message(self, event):
        """
        Nhận sự kiện từ Channel Layer Group và đẩy dữ liệu JSON về client WebSocket.
        
        Args:
            event (dict): Dữ liệu sự kiện được truyền từ group_send.
        """
        await self.send(text_data=json.dumps({
            'message_id': event.get('message_id'),
            'sender_name': event.get('sender_name', 'System'),
            'content': event.get('content', ''),
            'is_ai': event.get('is_ai', False),
        }))

    async def trigger_ai_response(self, user_query):
        """
        Khởi tạo RAGEngine gắn với `group_id` để truy vấn ChromaDB, gọi LLM 
        và gửi câu trả lời của AI lên kênh chat nhóm.
        
        Args:
            user_query (str): Câu hỏi hoặc nội dung tin nhắn của người dùng.
        """
        try:
            logger.info(f"[RAG Engine] Đang khởi tạo RAGEngine cho nhóm {self.group_id}...")
            rag_engine = RAGEngine(group_id=self.group_id)
            ai_reply_text = await rag_engine.query(query=user_query)

            ai_message_obj = await self.save_ai_message(self.group_id, ai_reply_text)
            logger.info(f"[RAG Engine] AI phản hồi thành công cho nhóm {self.group_id} (Msg ID: {ai_message_obj.id})")

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
        except Exception as e:
            logger.exception(f"[RAG Engine Error] Lỗi xử lý truy vấn AI trong nhóm {self.group_id}: {str(e)}")

    @database_sync_to_async
    def check_user_membership(self, user, group_id):
        """
        Kiểm tra xem người dùng có phải là thành viên hợp lệ của nhóm hay không (Tenant Isolation).
        
        Args:
            user (User): Đối tượng người dùng cần kiểm tra.
            group_id (int/str): Định danh nhóm làm việc.
            
        Returns:
            bool: True nếu tồn tại Membership, ngược lại False.
        """
        return Membership.objects.filter(user=user, group_id=group_id).exists()

    @database_sync_to_async
    def save_message(self, user, group_id, content):
        """
        Lưu tin nhắn của User vào Database, liên kết chặt chẽ với Tenant `group_id`.
        
        Args:
            user (User): Người gửi tin nhắn.
            group_id (int/str): Định danh nhóm làm việc.
            content (str): Nội dung tin nhắn.
            
        Returns:
            Message: Đối tượng tin nhắn vừa được tạo trong Database.
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
        """
        Lưu tin nhắn phản hồi từ AI vào Database với thông tin sender là thành viên AI của nhóm.
        
        Args:
            group_id (int/str): Định danh nhóm làm việc.
            content (str): Nội dung phản hồi từ AI Assistant.
            
        Returns:
            Message: Đối tượng tin nhắn AI vừa được tạo trong Database.
        """
        group = ChatGroup.objects.get(id=group_id)
        ai_membership = Membership.objects.filter(group=group, is_ai=True).first()
        return Message.objects.create(
            group=group,
            sender=ai_membership,
            content=content
        )

    @database_sync_to_async
    def check_user_membership(self, user, group_id):
        """
        Kiểm tra xem người dùng có phải là thành viên hợp lệ của nhóm hay không (Tenant Isolation).
        """
        return Membership.objects.filter(user=user, group_id=group_id).exists()