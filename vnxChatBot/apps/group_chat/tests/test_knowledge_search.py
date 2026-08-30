# -*- coding: utf-8 -*-
"""
Module: group_chat.test_knowledge_search
Description:
    Kiểm thử tự động cho API tìm kiếm tri thức nhóm (Knowledge Search API).
    Đảm bảo tính năng phân quyền nhóm (Tenant Isolation) và validate từ khóa chính xác.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.core.models import User
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter

class KnowledgeSearchViewsTestCase(TestCase):
    """
    Kịch bản kiểm thử API tìm kiếm tri thức nhóm (Search Knowledge API).
    """
    
    def setUp(self):
        # 1. Khởi tạo dữ liệu người dùng độc lập tránh lỗi IntegrityError
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
        Membership.objects.create(
            group=self.group,
            user=self.user_admin,
            role='admin'
        )
        
        # 4. Khởi tạo KnowledgeChapter đã được duyệt (approved) khớp với cấu trúc thực tế
        self.chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title='Kiến trúc Hybrid Search trong VnxChatBot',
            summary='Tài liệu chi tiết về kết hợp BM25 và Vector Search để tối ưu RAG hệ thống.',
            status='approved'
        )
        
        # 5. Khởi tạo HTTP Client
        self.client = Client()

    def test_search_knowledge_unauthorized(self):
        """Kiểm tra: Người dùng không thuộc nhóm không thể tìm kiếm tri thức."""
        self.client.login(username='stranger_user', password='password123')
        url = reverse('group_chat:search_knowledge', kwargs={'group_id': self.group.id})
        
        response = self.client.get(url, {'q': 'Kiến trúc Hybrid Search'})
        
        # Phải trả về lỗi 403 Forbidden do vi phạm phân quyền nhóm (Group-Centric)
        self.assertEqual(response.status_code, 403)

    def test_search_knowledge_invalid_query(self):
        """Kiểm tra: Từ khóa quá ngắn hoặc không đủ cụm từ sẽ bị chặn ở tầng API (HTTP 400)."""
        self.client.login(username='admin_user', password='password123')
        url = reverse('group_chat:search_knowledge', kwargs={'group_id': self.group.id})
        
        # Từ khóa ngắn (< 10 ký tự hoặc < 3 từ)
        response = self.client.get(url, {'q': 'Hybrid'})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['code'], 'invalid_search_query')
        self.assertIn('suggestions_list', data)

    def test_search_knowledge_success(self):
        """Kiểm tra: Thành viên trong nhóm tìm kiếm từ khóa hợp lệ thành công trên chương đã approved."""
        self.client.login(username='admin_user', password='password123')
        url = reverse('group_chat:search_knowledge', kwargs={'group_id': self.group.id})
        
        # Từ khóa hợp lệ (đủ dài và đủ từ)
        response = self.client.get(url, {'q': 'Kiến trúc Hybrid Search'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['title'], self.chapter.title)