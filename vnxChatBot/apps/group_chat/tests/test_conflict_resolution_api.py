# -*- coding: utf-8 -*-
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter

User = get_user_model()

class TestConflictResolutionAPI(APITestCase):
    """
    Test Suite kiểm thử các hành động giải quyết xung đột tri thức qua API View:
    - Overwrite / Update (Ghi đè, duyệt và đồng bộ VectorDB)
    - Ignore / Discard (Bỏ qua nội dung xung đột)
    - Merge / AI_Rewrite (Hợp nhất nội dung tùy chỉnh)
    """
    def setUp(self):
        self.user_in_group = User.objects.create_user(
            username="resolver_member", 
            email="resolver@example.com", 
            password="password"
        )
        self.group = ChatGroup.objects.create(name="Nhóm Xử Lý Xung Đột API")
        
        Membership.objects.create(
            user=self.user_in_group,
            group=self.group,
            role="member"
        )

        # Tạo KnowledgeChapter ở trạng thái xung đột
        self.chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title="Tài liệu xung đột cần xử lý",
            summary="Tóm tắt cũ",
            status="conflict_detected",
            suggested_content="Nội dung gợi ý hợp nhất từ AI",
            has_conflict=True
        )

        self.url = reverse('group_chat:conflict_resolution_api', kwargs={
            'group_id': self.group.id,
            'chapter_id': self.chapter.id
        })

    def test_resolve_conflict_overwrite(self):
        """Kiểm tra hành động ghi đè (overwrite): Chuyển status thành approved và tắt cờ conflict"""
        self.client.force_authenticate(user=self.user_in_group)
        response = self.client.post(self.url, {"action": "overwrite"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["current_status"], "approved")

        self.chapter.refresh_from_db()
        self.assertFalse(self.chapter.has_conflict)
        self.assertEqual(self.chapter.status, "approved")

    def test_resolve_conflict_ignore(self):
        """Kiểm tra hành động bỏ qua (ignore/discard): Chuyển status thành rejected"""
        self.client.force_authenticate(user=self.user_in_group)
        response = self.client.post(self.url, {"action": "ignore"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["current_status"], "rejected")

        self.chapter.refresh_from_db()
        self.assertFalse(self.chapter.has_conflict)
        self.assertEqual(self.chapter.status, "rejected")

    def test_resolve_conflict_merge(self):
        """Kiểm tra hành động hợp nhất (merge): Cập nhật summary mới và phê duyệt"""
        self.client.force_authenticate(user=self.user_in_group)
        response = self.client.post(self.url, {
            "action": "merge",
            "new_content": "Nội dung đã hợp nhất thủ công"
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "success")

        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.summary, "Nội dung đã hợp nhất thủ công")
        self.assertEqual(self.chapter.status, "approved")