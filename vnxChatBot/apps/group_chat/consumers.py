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
        Quản lý vòng đời kết nối WebSocket dựa trên định danh `group_id` (Tenant Isolation).
        Chịu trách nhiệm:
        1. Xác thực quyền hạn thành viên trong nhóm trước khi cho phép kết nối.
        2. Nhận tin nhắn từ Client, lưu vào Database dưới dạng bất đồng bộ (`database_sync_to_async`).
        3. Phát tán tin nhắn realtime tới toàn bộ thành viên trong Channel Layer Group.
        4. Kích hoạt cơ chế AI Listener (`@ai`) để gọi RAGEngine truy vấn tri thức và trả lời tự động.
    """

    # async def connect(self):
    #     """
    #     Thiết lập kết nối WebSocket, kiểm tra xác thực người dùng và phân quyền 
    #     truy cập vào ChatGroup cụ thể (Group-Centric Tenant).
    #     """
    #     self.group_id = self.scope['url_route']['kwargs']['group_id']
    #     self.room_group_name = f"chat_group_{self.group_id}"
        
    #     # Kiểm tra user đã đăng nhập chưa
    #     self.user = self.scope.get('user', AnonymousUser())
    #     if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
    #         await self.close()
    #         return

    #     # Kiểm tra user có thuộc nhóm này không (Group-Centric Tenant Security)
    #     is_member = await self.check_user_membership(self.user, self.group_id)
    #     if not is_member:
    #         await self.close()
    #         return

    #     # Tham gia vào Channel Layer Group của phòng chat
    #     await self.channel_layer.group_add(
    #         self.room_group_name,
    #         self.channel_name
    #     )
    #     await self.accept()

    async def connect(self):
        """
        Function: connect
        Description: 
            Xử lý khi có kết nối WebSocket từ client. 
            Kiểm tra xác thực user, phân quyền thành viên trong nhóm (Tenant isolation) 
            trước khi chấp nhận kết nối và đưa vào channel group.
        """
        self.user = self.scope["user"]
        self.group_id = self.scope["url_route"]["kwargs"].get("group_id")

        # Kiểm tra xác thực người dùng
        if not self.user.is_authenticated:
            await self.close()
            return

        # Kiểm tra quyền thành viên (Tenant-based Isolation)
        is_member = await self.check_user_membership(self.user, self.group_id)
        if not is_member:
            await self.close()
            return

        self.room_group_name = f"chat_{self.group_id}"

        # 🛡️ Kiểm tra an toàn channel_layer trước khi gọi group_add
        if self.channel_layer is None:
            print("❌ [CRITICAL ERROR] Channel layer is not configured properly in settings.py!")
            await self.close()
            return

        # Tham gia vào nhóm WebSocket
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """
        Rời khỏi Channel Layer Group khi client ngắt kết nối WebSocket nhằm giải phóng tài nguyên.
        
        Args:
            close_code (int): Mã trạng thái đóng kết nối từ phía client/server.
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Nhận dữ liệu dạng JSON từ client WebSocket khi thành viên gửi tin nhắn mới.
        Thực hiện lưu trữ tin nhắn người dùng và điều phối sự kiện phát tán realtime.

        Args:
            text_data (str): Chuỗi JSON chứa nội dung tin nhắn từ client gửi lên.
        """
        try:
            content = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = content.get('message', '').strip()
        if not message_text:
            return

        # 1. Lưu tin nhắn của người dùng vào DB bất đồng bộ (Gắn với Tenant group_id)
        message_obj = await self.save_message(self.user, self.group_id, message_text, is_ai=False)

        # 2. Phát tán tin nhắn của người dùng đến tất cả client trong nhóm theo thời gian thực
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
        # Chỉ kích hoạt nếu tin nhắn chứa cú pháp gọi tên AI('@ai')
        if '@ai' in message_text.lower():
            await self.trigger_ai_response(message_text)

    async def chat_message(self, event):
        """
        Nhận sự kiện từ Channel Layer và đẩy dữ liệu tin nhắn về lại client WebSocket dưới dạng JSON.

        Args:
            event (dict): Dictionary chứa thông tin tin nhắn được broadcast từ group_send.
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
        Khởi tạo RAGEngine gắn với định danh group_id của tenant hiện tại để truy vấn 
        tri thức nội bộ từ ChromaDB, sau đó gọi LLM sinh câu trả lời và broadcast ra nhóm.

        Args:
            user_query (str): Câu hỏi hoặc yêu cầu mà người dùng vừa gửi kèm từ khóa gọi AI.
        """
        # Khởi tạo RAGEngine kèm theo định danh group_id để đảm bảo tính cô lập dữ liệu (Tenant Isolation)
        rag_engine = RAGEngine(group_id=self.group_id)
        
        # Gọi phương thức truy vấn tri thức và sinh câu trả lời từ LLM thông qua AIFactory
        ai_reply_text = await rag_engine.query(query=user_query)

        # Lưu tin nhắn phản hồi của AI vào Database
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
        """
        Kiểm tra người dùng có phải là thành viên hợp lệ của nhóm hay không.
        Đảm bảo tính bảo mật tuyệt đối theo mô hình Tenant Isolation.

        Args:
            user (User): Đối tượng người dùng hiện tại.
            group_id (int/str): Định danh nhóm làm việc.

        Returns:
            bool: True nếu tồn tại Membership, ngược lại False.
        """
        # return Membership.objects.filter(user=user, chat_group_id=group_id).exists()
        return Membership.objects.filter(user=user, group_id=group_id).exists()
    

    @database_sync_to_async
    def save_message(self, user, group_id, content, is_ai=False):
        """
        Lưu tin nhắn của User vào Database, liên kết chặt chẽ với Tenant `group_id`.

        Args:
            user (User): Người gửi tin nhắn.
            group_id (int/str): Định danh nhóm làm việc.
            content (str): Nội dung tin nhắn.
            is_ai (bool): Cờ xác định có phải tin nhắn của AI hay không.

        Returns:
            Message: Đối tượng tin nhắn vừa được khởi tạo trong Database.
        """
        group = ChatGroup.objects.get(id=group_id)
        sender_membership = Membership.objects.filter(chat_group=group, user=user).first()
            
        return Message.objects.create(
            chat_group=group,
            sender=sender_membership,
            content=content
        )
    
    @database_sync_to_async
    def save_ai_message(self, group_id, content):
        """
        Lưu tin nhắn phản hồi từ AI vào Database. Người gửi được định nghĩa tự động 
        là thành viên AI trong nhóm (có cờ `is_ai=True`, không tạo User ảo).

        Args:
            group_id (int/str): Định danh nhóm làm việc.
            content (str): Nội dung câu trả lời từ AI.

        Returns:
            Message: Đối tượng tin nhắn của AI vừa được lưu thành công.
        """
        group = ChatGroup.objects.get(id=group_id)
        ai_membership = Membership.objects.filter(chat_group=group, is_ai=True).first()
        return Message.objects.create(
            chat_group=group,
            sender=ai_membership,
            content=content
        )