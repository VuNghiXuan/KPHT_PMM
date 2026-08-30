# -*- coding: utf-8 -*-
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, KnowledgeChapter, Membership

User = get_user_model()

class AIRewriteAPITestCase(APITestCase):
    def setUp(self):
        # 1. Khởi tạo User
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # 2. Tạo nhóm chat thử nghiệm
        self.group = ChatGroup.objects.create(name="Test Group")
        
        # 3. Tạo Membership cho User
        Membership.objects.create(group=self.group, user=self.user, role='member')
        
        # 4. Tạo chương tri thức chuẩn xác với group_id
        self.chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title="Chương mẫu", 
            summary="Nội dung gốc"
        )
        
        # 5. Khởi tạo URL endpoint chính
        self.url = reverse('group_chat:ai_rewrite', kwargs={
            'group_id': self.group.id,
            'chapter_id': self.chapter.id
        })
        self.client.force_authenticate(user=self.user)

    def test_rewrite_success(self):
        """Kiểm tra phản hồi thành công với dữ liệu hợp lệ."""
        data = {
            "chapter_id": str(self.chapter.id),
            "user_prompt": "Hãy viết lại nội dung này cho chuyên nghiệp hơn.",
            "action_type": "rewrite"
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Kiểm tra khớp với trường 'summary' mà View trả về
        self.assertIn('summary', response.data)

    def test_rewrite_invalid_prompt_length(self):
        """Kiểm tra chặn dữ liệu rác (prompt quá ngắn < 5 ký tự)."""
        data = {
            "chapter_id": str(self.chapter.id),
            "user_prompt": "abc",  # Dưới min_length
            "action_type": "rewrite"
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rewrite_invalid_action(self):
        """Kiểm tra chặn action_type không được hỗ trợ."""
        data = {
            "chapter_id": str(self.chapter.id),
            "user_prompt": "Viết lại nội dung này nhé.",
            "action_type": "hacking_action"
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rewrite_wrong_group_id(self):
        """Kiểm tra tính cô lập: Không được thao tác chương của nhóm khác."""
        other_group = ChatGroup.objects.create(name="Other Group")
        # Sử dụng đúng tham số group_id
        other_chapter = KnowledgeChapter.objects.create(
            group_id=other_group.id, 
            title="Chương lạ",
            summary="Nội dung nhóm khác"
        )
        
        # Tạo URL cố tình truy cập chương của nhóm khác thông qua group_id hiện tại
        wrong_url = reverse('group_chat:ai_rewrite', kwargs={
            'group_id': self.group.id,
            'chapter_id': other_chapter.id
        })
        
        data = {
            "chapter_id": str(other_chapter.id),
            "user_prompt": "Viết lại nội dung.",
            "action_type": "rewrite"
        }
        response = self.client.post(wrong_url, data, format='json')
        
        # Phải trả về 404 vì chương không thuộc group_id trong URL
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)