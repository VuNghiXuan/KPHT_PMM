# -*- coding: utf-8 -*-
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter

User = get_user_model()

class TestConflictChapterListAPI(APITestCase):
    def setUp(self):
        # 1. Tạo user với email riêng biệt để tránh lỗi UNIQUE constraint
        self.user_in_group = User.objects.create_user(
            username="member_conflict_test", 
            email="member_conflict@example.com", 
            password="password"
        )
        self.user_out_group = User.objects.create_user(
            username="outsider_conflict_test", 
            email="outsider_conflict@example.com", 
            password="password"
        )
        
        # 2. Khởi tạo ChatGroup theo chuẩn Modular Monolith
        self.group = ChatGroup.objects.create(name="Nhóm Xử Lý Xung Đột")
        
        # 3. Thêm thành viên vào nhóm thông qua model Membership chuẩn
        Membership.objects.create(
            user=self.user_in_group,
            group=self.group,
            role="member"
        )

        # 4. Tạo KnowledgeChapter ở trạng thái xung đột đúng theo model thực tế
        self.conflict_chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title="Tài liệu bảo mật v2",
            summary="Tóm tắt mới",
            status="conflict_detected",
            suggested_content="Nội dung hợp nhất từ AI",
            has_conflict=True,
            metadata={
                "reason": "Trùng lặp ngữ nghĩa với tài liệu ID 3",
                "conflict_with": [{"id": 3, "title": "Tài liệu cũ"}]
            }
        )

        # 5. Tạo một chapter bình thường để kiểm tra việc bộ lọc hoạt động chính xác (không được xuất hiện trong kết quả conflicts)
        self.normal_chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title="Tài liệu bình thường",
            summary="Tóm tắt bình thường",
            status="pending",
            has_conflict=False
        )

        self.url = reverse('group_chat:conflict_chapter_list_api', kwargs={'group_id': self.group.id})

    def test_get_conflict_chapters_success_and_data_accuracy(self):
        """Kiểm tra thành viên trong nhóm lấy danh sách xung đột thành công, đúng cấu trúc dữ liệu và lọc chuẩn xác"""
        self.client.force_authenticate(user=self.user_in_group)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Kiểm tra trạng thái phản hồi và số lượng bản ghi (chỉ lấy status='conflict_detected')
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 1)
        
        # Kiểm tra chi tiết cấu trúc dữ liệu trả về của tài liệu xung đột
        conflict_item = data["conflicts"][0]
        self.assertEqual(conflict_item["id"], self.conflict_chapter.id)
        self.assertEqual(conflict_item["title"], "Tài liệu bảo mật v2")
        self.assertEqual(conflict_item["summary"], "Tóm tắt mới")
        self.assertEqual(conflict_item["suggested_content"], "Nội dung hợp nhất từ AI")
        self.assertEqual(conflict_item["reason"], "Trùng lặp ngữ nghĩa với tài liệu ID 3")
        self.assertEqual(len(conflict_item["conflict_with"]), 1)
        self.assertEqual(conflict_item["conflict_with"][0]["title"], "Tài liệu cũ")

    def test_get_conflict_chapters_forbidden_for_outsider(self):
        """Kiểm tra người ngoài nhóm không được phép truy cập danh sách xung đột của nhóm"""
        self.client.force_authenticate(user=self.user_out_group)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)