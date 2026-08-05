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
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist

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
        Xử lý khi client ngắt kết nối WebSocket:
        1. Rời khỏi Channel Layer Group tương ứng của nhóm.
        2. Ghi log trạng thái ngắt kết nối một cách an toàn (tránh lỗi SynchronousOnlyOperation).
        """
        # Lấy trước giá trị username một cách an toàn từ scope nếu có thể
        username = "Unknown"
        if hasattr(self, 'scope') and 'user' in self.scope:
            user = self.scope['user']
            if user and user.is_authenticated:
                username = user.username

        # Rời khỏi nhóm phòng chat
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"[WebSocket] Ngắt kết nối: User '{username}' rời khỏi {self.room_group_name} (Code: {close_code})")

    async def receive(self, text_data):
        """
        Xử lý dữ liệu nhận từ Client qua WebSocket, thực hiện:
        1. Giải mã JSON payload từ client gửi lên.
        2. Lưu tin nhắn của User vào Database (bất đồng bộ thông qua save_message).
        3. Truy xuất an toàn quan hệ trích dẫn (reply_to) bằng sync_to_async để tránh lỗi SynchronousOnlyOperation.
        4. Broadcast tin nhắn kèm thông tin trích dẫn tới toàn bộ thành viên trong nhóm.
        5. Kiểm tra điều kiện (Guardrail): Chỉ kích hoạt AI RAG Engine khi thỏa điều kiện gọi AI.

        Args:
            text_data (str): Chuỗi JSON chứa nội dung tin nhắn và tùy chọn reply_to_id.
        """
        try:
            data = json.loads(text_data)
            message_text = data.get("message", "").strip()
            reply_to_id = data.get("reply_to_id")  # 📥 Nhận ID tin nhắn gốc từ client
            
            if not message_text:
                logger.debug("[WebSocket] Nhận tin nhắn rỗng từ client, bỏ qua xử lý.")
                return

            logger.info(f"[WebSocket] Nhận tin nhắn từ '{self.user.username}' trong nhóm {self.group_id}: '{message_text[:50]}...'")

            # 1. Lưu tin nhắn của User vào Database (Hỗ trợ reply_to_id và Tenant Isolation)
            message_obj = await self.save_message(self.user, self.group_id, message_text, reply_to_id=reply_to_id)
            
            # 2. Chuẩn bị dữ liệu trích dẫn (reply_data) một cách an toàn để tránh lỗi đồng bộ ORM
            reply_data = None
            if reply_to_id:
                @sync_to_async
                def get_reply_metadata():
                    try:
                        # 🛡️ Truy vấn an toàn thông qua bảng Membership, kết nối ngược về User
                        original_msg = Message.objects.select_related('sender', 'sender__user', 'group').get(
                            id=reply_to_id, 
                            group_id=self.group_id
                        )
                        sender = original_msg.sender
                        
                        # 🔍 Xác định tên người gửi dựa trên cờ is_ai và sự tồn tại của tài khoản User
                        if sender:
                            if getattr(sender, 'is_ai', False):
                                sender_name = "AI Assistant"
                            elif sender.user and hasattr(sender.user, 'username'):
                                sender_name = sender.user.username
                            else:
                                sender_name = "Thành viên nhóm"
                        else:
                            sender_name = "Hệ thống"

                        return {
                            'id': original_msg.id,
                            'sender_name': sender_name,
                            'content': original_msg.content[:100]  # Cắt ngắn nội dung hiển thị trích dẫn
                        }
                    except ObjectDoesNotExist:
                        logger.warning(f"[WebSocket] Không tìm thấy tin nhắn gốc ID {reply_to_id} trong nhóm {self.group_id}")
                        return None
                    except Exception as e:
                        logger.error(f"[WebSocket] Lỗi truy vấn metadata tin nhắn gốc: {str(e)}")
                        return None

                # Gọi hàm async đúng cú pháp (loại bỏ dấu hai chấm thừa)
                reply_data = await get_reply_metadata()

            # 3. Broadcast tin nhắn kèm thông tin trích dẫn tới toàn bộ thành viên trong nhóm
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_id": message_obj.id,
                    "sender_name": self.user.username,
                    "content": message_text,
                    "is_ai": False,
                    "reply_to": reply_data,  # 📥 Chứa thông tin trích dẫn an toàn
                    "created_at": message_obj.created_at.strftime('%H:%M') if hasattr(message_obj, 'created_at') else "",
                }
            )

            # 4. Intelligent Guardrail: Kiểm tra xem có nên gọi AI hay không?
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
        except Exception as e:
            logger.exception(f"[WebSocket Error] Lỗi hệ thống khi xử lý receive message: {str(e)}")

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
        Sự kiện xử lý khi có thông điệp broadcast từ channel_layer.
        Nhiệm vụ: Nhận toàn bộ dữ liệu (bao gồm cả reply_to metadata) và chuyển tiếp xuống Client qua WebSocket.
        """
        try:
            # Lấy payload dữ liệu từ event group_send
            message_id = event.get("message_id")
            sender_name = event.get("sender_name")
            content = event.get("content")
            is_ai = event.get("is_ai", False)
            reply_to_data = event.get("reply_to")  # 📥 Đảm bảo hứng trọn dữ liệu trích dẫn
            created_at = event.get("created_at")

            # Đẩy dữ liệu cấu trúc hoàn chỉnh xuống Client JavaScript
            await self.send(text_data=json.dumps({
                "message_id": message_id,
                "sender_name": sender_name,
                "content": content,
                "is_ai": is_ai,
                "reply_to": reply_to_data,  # 👈 Gửi metadata trích dẫn sang client để render giao diện
                "created_at": created_at
            }))
        except Exception as e:
            logger.error(f"[WebSocket Error] Lỗi khi broadcast chat_message tới client: {str(e)}")

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
    def save_message(self, user, group_id, content, reply_to_id=None):
        """
        Lưu tin nhắn của User vào Database, liên kết chặt chẽ với Tenant `group_id`, 
        hỗ trợ tính năng trích dẫn phản hồi tin nhắn (reply_to).
        
        Args:
            user (User): Người gửi tin nhắn.
            group_id (int/str): Định danh nhóm làm việc.
            content (str): Nội dung tin nhắn.
            reply_to_id (int, optional): ID tin nhắn gốc nếu đây là tin nhắn trả lời.
            
        Returns:
            Message: Đối tượng tin nhắn vừa được tạo trong Database.
        """
        group = ChatGroup.objects.get(id=group_id)
        sender_membership = Membership.objects.filter(group=group, user=user).first()
        
        reply_message = None
        if reply_to_id:
            try:
                reply_message = Message.objects.get(id=reply_to_id, group=group)
            except Message.DoesNotExist:
                pass
            
        return Message.objects.create(
            group=group,  
            sender=sender_membership,
            content=content,
            reply_to=reply_message
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

    # Trong phương thức nhận tin nhắn của ChatConsumer (ví dụ: receive hoặc receive_json)
    async def receive_json(self, content):
        message_text = content.get('message', '').strip()
        reply_to_id = content.get('reply_to_id') # Lấy ID tin nhắn gốc nếu có
        
        if not message_text:
            return

        # 1. Lưu tin nhắn vào Database
        message = await self.save_message(message_text, reply_to_id)
        
        # 2. Chuẩn bị dữ liệu gửi đi qua Channel Layer
        reply_data = None
        if message.reply_to:
            reply_data = {
                'id': message.reply_to.id,
                'sender_name': message.reply_to.sender.user.username if not message.reply_to.sender.is_ai else "AI Assistant",
                'content': message.reply_to.content[:100] # Cắt ngắn nội dung trích dẫn
            }

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'content': message.content,
                'sender_name': self.scope['user'].username,
                'is_ai': False,
                'avatar_url': self.scope['user'].profile.avatar.url if hasattr(self.scope['user'], 'profile') and self.scope['user'].profile.avatar else "",
                'reply_to': reply_data,
                'created_at': message.created_at.strftime('%H:%M'),
            }
        )

    