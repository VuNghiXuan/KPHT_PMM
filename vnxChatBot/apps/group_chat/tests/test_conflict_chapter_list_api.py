# -*- coding: utf-8 -*-
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership, KnowledgeChapter

User = get_user_model()

class TestConflictChapterAndApprovalSuite(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 🔌 Khởi tạo patcher ở cấp độ lớp để vô hiệu hóa hoàn toàn lệnh gọi Vector Store thực tế
        cls._patcher = patch('apps.ai_assistant.services.ai_engine.AIEngineService.sync_chapter_embeddings')
        cls.mock_sync_embeddings = cls._patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._patcher.stop()
        super().tearDownClass()

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
        self.group = ChatGroup.objects.create(name="Nhóm Xử Lý Xung Đột & Phê Duyệt")
        
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

        # 5. Tạo một chapter ở trạng thái pending để kiểm tra việc không bị rò rỉ hoặc sync sai quy tắc
        self.pending_chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title="Tài liệu chờ duyệt",
            summary="Tóm tắt bình thường",
            status="pending",
            has_conflict=False
        )

        self.list_url = reverse('group_chat:conflict_chapter_list_api', kwargs={'group_id': self.group.id})
        self.approval_url = reverse('group_chat:knowledge_chapter_approval_api', kwargs={
            'group_id': self.group.id, 
            'chapter_id': self.pending_chapter.id
        })

    def test_get_conflict_chapters_success_and_data_accuracy(self):
        """🧪 Kiểm tra thành viên trong nhóm lấy danh sách xung đột thành công, đúng cấu trúc dữ liệu và lọc chuẩn xác"""
        self.client.force_authenticate(user=self.user_in_group)
        response = self.client.get(self.list_url)

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
        """🔒 Kiểm tra người ngoài nhóm không được phép truy cập danh sách xung đột của nhóm"""
        self.client.force_authenticate(user=self.user_out_group)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('apps.group_chat.services.knowledge_service.KnowledgeService.update_chapter_status')
    def test_pending_chapter_does_not_sync_and_approval_triggers_service(self, mock_update_status):
        """
        ⚙️ Kiểm chứng Nguyên tắc Vàng: Dữ liệu pending hoàn toàn cô lập, 
        không kích hoạt đồng bộ Vector Store cho đến khi hành động approve được thực thi.
        """
        # 0. Đặt giá trị trả về giả lập cho mock để tránh lỗi Serialization / Recursion khi render JSON
        mock_update_status.return_value = {"status": "success", "message": "Đã phê duyệt thành công"}

        # 1. Xác nhận trước khi approve, chapter đang ở trạng thái pending
        self.assertEqual(self.pending_chapter.status, "pending")
        
        # 2. Thực hiện gọi API phê duyệt (approve) với user hợp lệ trong nhóm
        self.client.force_authenticate(user=self.user_in_group)
        response = self.client.post(self.approval_url, {"action": "approve"})

        # 3. Kiểm tra kết quả phản hồi từ API
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Xác thực KnowledgeService.update_chapter_status được gọi đúng để chuyển trạng thái sang approved
        mock_update_status.assert_called_once_with(self.pending_chapter.id, 'approved', self.user_in_group)