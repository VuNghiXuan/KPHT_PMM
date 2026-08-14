"""
Tên tệp: apps/group_chat/test_ai_config.py
Mô tả: Unit Test cho Group-Centric AI Configuration.
       Truyền đúng cấu trúc JSON payload (ai_provider, ai_model, custom_api_key) 
       để khớp tuyệt đối với update_ai_config_view, triệt tiêu hoàn toàn lỗi 400 Bad Request.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.models, apps.core.models
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User
from apps.group_chat.models import ChatGroup, Membership
from apps.ai_assistant.models import GroupAIProvider

class TestAIConfigView(TestCase):
    """
    Class: TestAIConfigView
    Mô tả: Unit Test kiểm tra tính năng cấu hình AI tập trung theo mô hình Group-Centric.
    """

    def setUp(self):
        """Thiết lập dữ liệu ban đầu cho kịch bản test cấu hình AI với client vô hiệu hóa kiểm tra CSRF."""
        self.client = Client(enforce_csrf_checks=False)
        
        self.user = User.objects.create_user(
            username='config_admin', 
            email='config_admin@example.com', 
            password='password123'
        )
        self.other_user = User.objects.create_user(
            username='outsider', 
            email='outsider@example.com', 
            password='password123'
        )
        
        # Khởi tạo ChatGroup
        self.group = ChatGroup.objects.create(name='Nhóm Cấu Hình AI')
        
        # Phân quyền admin cho user trong nhóm
        Membership.objects.create(user=self.user, group=self.group, role='admin')
        
        # URL cập nhật cấu hình AI của nhóm
        self.url = reverse('group_chat:update_ai_config', kwargs={'group_id': self.group.id})

    def test_update_config_success(self):
        """Kiểm tra luồng cập nhật cấu hình hợp lệ bởi thành viên có quyền admin."""
        self.client.login(username='config_admin', password='password123')
        
        # Gửi dữ liệu dưới dạng JSON payload khớp với cấu trúc view yêu cầu (ai_provider, ai_model, custom_api_key)
        payload = {
            'ai_provider': 'gemini',
            'ai_model': 'gemini-1.5-pro',
            'custom_api_key': 'AIzaSyTestKey12345'
        }
        
        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json',
            follow=True
        )
        
        # Kiểm tra HTTP Status trả về phải là 200 Success
        self.assertEqual(response.status_code, 200)
        
        # Kiểm tra dữ liệu đã được cập nhật thành công vào Database thông qua model GroupAIProvider
        ai_config = GroupAIProvider.objects.filter(group=self.group).first()
        self.assertIsNotNone(ai_config, "Bản ghi GroupAIProvider phải được khởi tạo hoặc cập nhật.")
        self.assertEqual(ai_config.provider, 'gemini')
        self.assertEqual(ai_config.model_name, 'gemini-1.5-pro')

    def test_unauthorized_access(self):
        """Kiểm tra không cho phép người dùng không thuộc nhóm thay đổi cấu hình."""
        self.client.login(username='outsider', password='password123')
        
        payload = {
            'ai_provider': 'groq',
            'ai_model': 'llama3-70b',
            'custom_api_key': 'some_key'
        }
        
        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        
        # Hệ thống phải từ chối quyền truy cập với mã 403 Forbidden
        self.assertEqual(response.status_code, 403)

"""
set PYTHONPATH=.
set DJANGO_SETTINGS_MODULE=config.settings
python -m pytest apps/group_chat/test_ai_config.py
"""