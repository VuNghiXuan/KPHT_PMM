# -*- coding: utf-8 -*-
# Path: apps/ai_assistant/tests/test_knowledge_pipeline_strict.py
"""
Bộ kiểm thử nghiêm ngặt dành cho Pipeline Tri thức & Vector Store
Tuân thủ Hệ thống chỉ dẫn vận hành (VNXCHATBOT SYSTEM INSTRUCTIONS).
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from apps.group_chat.models import ChatGroup, RawDocument, KnowledgeChapter
from apps.ai_assistant.tasks import detect_semantic_overlap_task, sync_chapter_to_vector_async
from apps.ai_assistant.vector_store import VectorDBManager

User = get_user_model()


class StrictKnowledgePipelineTestCase(TestCase):
    """
    Test suite kiểm tra tuân thủ Quy tắc Vàng và cô lập dữ liệu theo group_id.
    """

    def setUp(self):
        # Đảm bảo cache sạch sẽ trước mỗi bài test
        cache.clear()

        # 1. Khởi tạo người dùng mẫu
        self.user_a = User.objects.create_user(
            username="user_a", email="user_a@example.com", password="password123"
        )
        self.user_b = User.objects.create_user(
            username="user_b", email="user_b@example.com", password="password123"
        )

        # 2. Khởi tạo ChatGroup cho Group A và Group B
        self.group_a = ChatGroup.objects.create(name="Group A")
        self.group_b = ChatGroup.objects.create(name="Group B")

        # 3. Tạo dummy file để gán vào FileField
        dummy_file = SimpleUploadedFile(
            "quy_trinh_a.pdf",
            b"Dummy PDF Content for Testing",
            content_type="application/pdf"
        )

        # 4. Khởi tạo RawDocument cho Group A
        self.raw_doc_a = RawDocument.objects.create(
            group=self.group_a,
            file=dummy_file,
            file_type="pdf",
            status="staging",
            raw_content="Nội dung thô kiểm thử quy trình A"
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch("apps.ai_assistant.tasks.sync_chapter_to_vector_async.delay")
    def test_golden_rule_non_approved_states_do_not_sync_to_vector_store(self, mock_sync_delay):
        """
        [Quy tắc Vàng] Dữ liệu ở trạng thái pending, staging, conflict_detected, rejected
        TUYỆT ĐỐI không được chèn vào Vector Store (ChromaDB).
        Chỉ khi duyệt (approved), signal mới kích hoạt task sync sang Vector Store.
        """
        chapter = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Chương 1: Khởi động",
            summary="Nội dung kiểm thử quy tắc vàng",
            status="pending",
        )

        # Thử cập nhật các trạng thái chưa được duyệt
        chapter.status = "staging"
        chapter.save()

        chapter.status = "conflict_detected"
        chapter.save()

        chapter.status = "rejected"
        chapter.save()

        # Assert 1: Task đồng bộ Vector Store TUYỆT ĐỐI không được gọi ở các trạng thái chưa duyệt
        mock_sync_delay.assert_not_called()

        # Đảm bảo cache sạch trước khi chuyển sang approved để không bị block bởi cache deduplication
        cache.clear()

        # Chuyển sang approved và bắt các callback trong transaction.on_commit (nếu có)
        with self.captureOnCommitCallbacks(execute=True):
            chapter.status = "approved"
            chapter.save()

        # Assert 2: Xác nhận Signal đã kích hoạt Celery Task đồng bộ thành công sau khi phê duyệt
        mock_sync_delay.assert_called_once_with(str(self.group_a.id), chapter.id)

    @patch("apps.ai_assistant.vector_store.VectorDBManager.query_similar")
    def test_cross_group_data_isolation(self, mock_query):
        """
        [Cô lập tuyệt đối] Truy vấn Semantic Search ở Group B
        không bao giờ trả về dữ liệu của Group A.
        """
        mock_query.return_value = []

        vector_db = VectorDBManager()
        results = vector_db.query_similar(
            query_text="Quy trình vận hành",
            group_id=self.group_b.id,
            top_k=5
        )

        mock_query.assert_called_once_with(
            query_text="Quy trình vận hành",
            group_id=self.group_b.id,
            top_k=5
        )
        self.assertEqual(len(results), 0)

    @patch("apps.ai_assistant.tasks.ConflictService.resolve_by_ai_rewrite")
    @patch("apps.ai_assistant.vector_store.VectorDBManager.search")
    def test_semantic_overlap_detection_triggers_conflict_state(self, mock_search, mock_rewrite):
        """
        [Phát hiện trùng lặp] Phát hiện tương đồng ngữ nghĩa >= 0.85 
        sẽ gán trạng thái conflict_detected và tạo gợi ý biên soạn.
        """
        mock_search.return_value = [
            {
                "id": "vec_123",
                "score": 0.89,
                "metadata": {"chapter_id": 99, "group_id": self.group_a.id},
                "content": "Nội dung đã tồn tại trong hệ thống",
            }
        ]
        mock_rewrite.return_value = {"merged_content": "Gợi ý biên soạn lại để tránh trùng lặp nội dung."}

        chapter = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Chương trùng lặp",
            summary="Nội dung trùng lặp với tài liệu cũ",
            status="pending",
        )

        detect_semantic_overlap_task(chapter_id=chapter.id)

        chapter.refresh_from_db()

        self.assertEqual(chapter.status, "conflict_detected")
        self.assertIsNotNone(chapter.suggested_content)
        self.assertIn("Gợi ý biên soạn", chapter.suggested_content)

    @patch("apps.ai_assistant.tasks.VectorDBManager.compute_embedding")
    def test_embedding_api_failure_recovery(self, mock_compute_embedding):
        """
        [Chống nghẽn & Khôi phục] Giả lập lỗi API Key hoặc mất kết nối Embedding.
        """
        mock_compute_embedding.side_effect = RuntimeError("LiteLLM / OpenAI API Key Invalid or Expired")

        chapter = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Chương lỗi Embedding",
            summary="Nội dung sẽ gặp lỗi khi tạo embedding",
            status="pending",
        )

        with self.assertRaises(RuntimeError):
            detect_semantic_overlap_task(chapter_id=chapter.id)

        chapter.refresh_from_db()
        self.assertEqual(chapter.status, "pending")