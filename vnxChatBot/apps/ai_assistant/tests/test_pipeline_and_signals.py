# -*- coding: utf-8 -*-
# Path: apps/ai_assistant/tests/test_pipeline_and_signals.py

from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.group_chat.models import RawDocument, KnowledgeChapter, ChatGroup
from apps.ai_assistant.models.text_choices import KnowledgeStatus
from apps.ai_assistant.tasks import (
    process_document_task,
    detect_semantic_overlap_task,
    sync_chapter_to_vector_async
)


class KnowledgePipelineAndSignalsTestCase(TestCase):
    def setUp(self):
        """Khởi tạo môi trường test cô lập cho 2 Group riêng biệt."""
        # 🟢 Khởi tạo ChatGroup (Django tự động sinh UUID cho ID)
        self.group_a = ChatGroup.objects.create(name="Group Alpha")
        self.group_b = ChatGroup.objects.create(name="Group Beta")

        # 🟢 Khởi tạo RawDocument gắn với group_a
        self.raw_doc_a = RawDocument.objects.create(
            group=self.group_a,
            raw_content="Quy trình Vận hành A",
            file_type="pdf",
            status="staging"
        )

    @patch("apps.ai_assistant.tasks.DocumentProcessorService")
    @patch("apps.ai_assistant.tasks.detect_semantic_overlap_task.s")
    def test_p1_process_document_task_flow(self, mock_p2_task_s, mock_doc_service):
        """Test P1: Phân rã tài liệu thành Chapter nháp & kiểm tra trùng lặp nội bộ/tiêu đề."""
        mock_chapter = KnowledgeChapter.objects.create(
            group=self.group_a,
            title="Chương 1: Giới thiệu",
            summary="Nội dung giới thiệu quy trình",
            status=KnowledgeStatus.PENDING,
            metadata={}
        )
        mock_doc_service.process_and_index.return_value = True
        mock_doc_service.create_draft_chapters_from_raw.return_value = [mock_chapter]

        result = process_document_task(
            raw_document_id=self.raw_doc_a.id,
            group_id=self.group_a.id,
            user_id=1
        )

        self.assertEqual(result["status"], "success")
        self.raw_doc_a.refresh_from_db()
        
        # Kiểm tra trạng thái tài liệu chuyển sang COMPLETED (hoặc completed tùy logic task)
        self.assertIn(self.raw_doc_a.status.upper(), ["COMPLETED", "SUCCESS"])
        mock_p2_task_s.assert_called_with(mock_chapter.id)

    @patch("apps.ai_assistant.tasks.VectorDBManager")
    @patch("apps.ai_assistant.tasks.ConflictService")
    def test_p2_detect_semantic_overlap_isolation(self, mock_conflict_service, mock_vector_db):
        """Test P2: Kiểm tra độ tương đồng Cosine & đảm bảo cô lập theo group_id."""
        chapter = KnowledgeChapter.objects.create(
            group=self.group_a,
            title="Kiến thức Bảo mật",
            summary="Các quy định về an toàn thông tin",
            status=KnowledgeStatus.PENDING
        )

        mock_vector_db.compute_embedding.return_value = [0.1, 0.2, 0.3]
        mock_vector_db.search.return_value = [{"id": 99, "score": 0.88}]
        mock_conflict_service.resolve_by_ai_rewrite.return_value = {
            "merged_content": "Gợi ý tổng hợp nội dung mới"
        }

        detect_semantic_overlap_task(chapter_id=chapter.id)

        # 🟢 Kiểm tra Vector Search bắt buộc phải truyền UUID của group_a
        mock_vector_db.search.assert_called_once_with(
            embedding=[0.1, 0.2, 0.3],
            group_id=self.group_a.id,
            limit=1,
            threshold=0.85
        )

        # 🟢 Kiểm tra cập nhật trạng thái khi phát hiện trùng lặp
        chapter.refresh_from_db()
        self.assertEqual(chapter.status, KnowledgeStatus.CONFLICT_DETECTED)
        self.assertTrue(chapter.has_conflict)
        self.assertIn("ai_rewrite_suggestion", chapter.metadata)

    @patch("apps.ai_assistant.tasks.DocumentProcessorService")
    @patch("apps.ai_assistant.tasks.VectorDBManager")
    def test_golden_rule_vector_store_sync(self, mock_vector_db, mock_doc_service):
        """Test P3 & Signals: Quy tắc vàng - Chặn dữ liệu chưa duyệt vào VectorDB."""
        chapter = KnowledgeChapter.objects.create(
            group=self.group_a,
            title="Chương chưa duyệt",
            summary="Nội dung nháp",
            status=KnowledgeStatus.PENDING
        )

        # Kịch bản 1: Chapter ở trạng thái PENDING -> Chặn đồng bộ & xóa embedding cũ nếu có
        res = sync_chapter_to_vector_async(group_id_str=str(self.group_a.id), chapter_id=chapter.id)
        self.assertIn("skipped: Not approved", res)
        
        # 🟢 Kiểm tra việc xóa khỏi VectorDB truyền chính xác UUID
        mock_vector_db.delete_unit_embeddings.assert_called_with(
            unit_id=chapter.id, 
            group_id=chapter.group_id
        )
        mock_doc_service.commit_chapter_to_vector_db.assert_not_called()

        # Kịch bản 2: Duyệt Chapter (APPROVED) -> Cho phép đồng bộ vào VectorDB
        chapter.status = KnowledgeStatus.APPROVED
        chapter.save()

        mock_doc_service.commit_chapter_to_vector_db.return_value = True
        res_approved = sync_chapter_to_vector_async(group_id_str=str(self.group_a.id), chapter_id=chapter.id)
        self.assertIn("synced successfully", res_approved)
        mock_doc_service.commit_chapter_to_vector_db.assert_called_with(chapter)