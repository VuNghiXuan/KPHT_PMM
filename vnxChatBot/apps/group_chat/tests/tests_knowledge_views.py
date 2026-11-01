# -*- coding: utf-8 -*-
"""
Module: group_chat.tests_knowledge_views
Description:
    Kiểm thử tự động cho các API Views quản lý vòng đời tri thức và chương mục (Knowledge Chapter Views).
    Đảm bảo tính năng phân quyền nhóm (Tenant Isolation) và phê duyệt hoạt động chính xác.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter

class KnowledgeViewsTestCase(TestCase):
    """
    Kịch bản kiểm thử API Views quản lý tri thức nhóm.
    """
    
    def setUp(self):
        # 1. Khởi tạo dữ liệu người dùng với email độc lập tránh lỗi IntegrityError
        self.user_admin = User.objects.create_user(
            username='admin_user', 
            email='admin_user@example.com', 
            password='password123'
        )
        self.user_stranger = User.objects.create_user(
            username='stranger_user', 
            email='stranger_user@example.com', 
            password='password123'
        )
        
        # 2. Khởi tạo nhóm chat (ChatGroup)
        self.group = ChatGroup.objects.create(name='Nhóm Kỹ Thuật AI')
        
        # 3. Gán quyền Admin cho user_admin trong nhóm
        self.membership_admin = Membership.objects.create(
            group=self.group,
            user=self.user_admin,
            role='admin'
        )
        
        # 4. Khởi tạo một KnowledgeChapter mẫu khớp hoàn toàn với cấu trúc Model thực tế
        self.chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title='Kiến trúc Hybrid Search trong VnxChatBot',
            summary='Tài liệu chi tiết về kết hợp BM25 và Vector Search.',
            status='pending'
        )
        
        # 5. Khởi tạo HTTP Client
        self.client = Client()

    def test_knowledge_chapter_list_unauthorized(self):
        """Kiểm tra: Người dùng không thuộc nhóm không thể xem danh sách tri thức."""
        self.client.login(username='stranger_user', password='password123')
        url = reverse('group_chat:knowledge_chapter_list', kwargs={'group_id': self.group.id})
        
        response = self.client.get(url, {'format': 'json'})
        
        # Phải trả về lỗi 403 Forbidden do vi phạm phân quyền nhóm
        self.assertEqual(response.status_code, 403)

    def test_knowledge_chapter_list_success(self):
        """Kiểm tra: Thành viên trong nhóm có thể lấy danh sách chương mục chờ duyệt thành công."""
        self.client.login(username='admin_user', password='password123')
        url = reverse('group_chat:knowledge_chapter_list', kwargs={'group_id': self.group.id})
        
        response = self.client.get(url, {'format': 'json'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['chapters']), 1)
        self.assertEqual(data['chapters'][0]['title'], self.chapter.title)

    def test_approve_chapter_action(self):
        """Kiểm tra: Quản trị viên thực hiện duyệt (approve) thành công một KnowledgeChapter."""
        self.client.login(username='admin_user', password='password123')
        url = reverse('group_chat:approve_reject_chapter', kwargs={'group_id': self.group.id, 'chapter_id': self.chapter.id})
        
        response = self.client.post(url, {'action': 'approve'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Kiểm tra lại trạng thái trong Database
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, 'approved')

    def test_reject_chapter_action(self):
        """Kiểm tra: Quản trị viên thực hiện từ chối/thu hồi (reject) chương mục tri thức."""
        self.client.login(username='admin_user', password='password123')
        url = reverse('group_chat:approve_reject_chapter', kwargs={'group_id': self.group.id, 'chapter_id': self.chapter.id})
        
        response = self.client.post(url, {'action': 'reject'})
        
        self.assertEqual(response.status_code, 200)
        
        # Kiểm tra lại trạng thái đã được chuyển sang rollback hoặc tương đương
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, 'rollback')