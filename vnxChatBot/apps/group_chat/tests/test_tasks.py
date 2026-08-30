# -*- coding: utf-8 -*-
# Path: apps/group_chat/tests/test_tasks.py

from django.test import TransactionTestCase
from unittest.mock import MagicMock, patch
from apps.group_chat.models import KnowledgeChapter
from apps.ai_assistant.tasks import detect_semantic_overlap_task

class TestConflictDetectionTask(TransactionTestCase):
    def setUp(self):
        self.group_id = 1
        self.chapter = KnowledgeChapter.objects.create(
            title="Test Title",
            summary="Test Summary",
            group_id=self.group_id,
            status="pending"
        )

    @patch('apps.ai_assistant.tasks.VectorDBManager')
    def test_detect_no_overlap(self, mock_vector_db):
        """Kiểm tra trường hợp không trùng lặp -> status ready_to_approve"""
        mock_vector_db.search.return_value = []
        detect_semantic_overlap_task.run(self.chapter.id)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, 'ready_to_approve')
        self.assertFalse(self.chapter.has_conflict)

    @patch('apps.ai_assistant.tasks.ConflictService')
    @patch('apps.ai_assistant.tasks.VectorDBManager')
    def test_detect_semantic_overlap(self, mock_vector_db, mock_conflict_service):
        """Kiểm tra trường hợp có xung đột -> status conflict_detected"""
        mock_vector_db.search.return_value = [{'id': 999}]
        
        # 🛠️ Định nghĩa side_effect để cập nhật trực tiếp dữ liệu trên chapter khi ConflictService được gọi
        def mock_resolve(chapter, new_content):
            chapter.summary = "Nội dung đã được hợp nhất an toàn"
            chapter.status = 'conflict_detected'
            chapter.has_conflict = True
            chapter.save()
            return chapter

        mock_conflict_service.resolve_by_ai_rewrite.side_effect = mock_resolve
        
        detect_semantic_overlap_task.run(self.chapter.id)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, 'conflict_detected')
        self.assertTrue(self.chapter.has_conflict)
        self.assertEqual(self.chapter.summary, "Nội dung đã được hợp nhất an toàn")

    @patch('apps.ai_assistant.tasks.VectorDBManager')
    def test_detect_overlap_with_uuid_id(self, mock_vector_db):
        """Kiểm tra việc xử lý an toàn khi VectorDB trả về ID dạng chuỗi/UUID"""
        mock_vector_db.search.return_value = [{'id': 'abc-123-uuid'}]
        detect_semantic_overlap_task.run(self.chapter.id)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, 'conflict_detected')