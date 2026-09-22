# -*- coding: utf-8 -*-
# Path: apps/group_chat/tests/test_tasks.py

from django.test import TransactionTestCase
from unittest.mock import MagicMock, patch
from apps.group_chat.models import KnowledgeChapter, RawDocument, ChatGroup
from apps.ai_assistant.tasks import process_document_task, detect_semantic_overlap_task


class TestP1PipelineAndDeduplication(TransactionTestCase):
    """
    Tệp kiểm thử toàn diện cho Pipeline P1:
    - Lớp 1: Hash Check (Lọc trùng nội bộ trong cùng file upload)
    - Lớp 2: SQL Check (Lọc trùng tiêu đề với DB hiện tại)
    - Lớp 3: VectorDB Check (Phát hiện trùng ngữ nghĩa - Cosine Similarity)
    - Quy tắc Vàng: Ngăn rò rỉ dữ liệu pending vào Vector Store
    """

    def setUp(self):
        # 1. Khởi tạo ChatGroup thực tế để thỏa mãn khóa ngoại (Foreign Key)
        self.chat_group = ChatGroup.objects.create(
            name="Nhóm Test Pipeline P1",
            description="Dùng để test khóa ngoại và Celery Tasks"
        )
        self.group_id = self.chat_group.id
        self.user_id = 100

        # 2. Tạo RawDocument liên kết đúng với chat_group
        self.raw_doc = RawDocument.objects.create(
            group=self.chat_group,
            status='STAGING'
        )

        # 3. Tạo Chapter mẫu liên kết chuẩn theo group_id (Hard Scoping)
        self.chapter = KnowledgeChapter.objects.create(
            title="Test Title",
            summary="Test Summary",
            group_id=self.group_id,
            status="pending",
            metadata={"raw_document_id": str(self.raw_doc.id)}
        )

    # ==========================================
    # 🧪 TEST CASES LỚP 1 & LỚP 2 (process_document_task)
    # ==========================================

    @patch('apps.ai_assistant.tasks.chain')
    @patch('apps.ai_assistant.tasks.DocumentProcessorService')
    def test_process_document_layer1_hash_deduplication(self, mock_processor, mock_chain):
        """
        [Lớp 1] Kiểm tra lọc trùng nội bộ: Nếu 1 file có 2 chương nội dung trùng hệt nhau,
        chương thứ 2 phải chuyển ngay thành 'conflict_detected' mà không đưa vào Task Chain Lớp 3.
        """
        c1 = KnowledgeChapter.objects.create(
            group_id=self.group_id,
            title="Bài 1", 
            summary="Nội dung trùng lặp", 
            status="pending",
            metadata={"raw_document_id": str(self.raw_doc.id)}
        )
        c2 = KnowledgeChapter.objects.create(
            group_id=self.group_id,
            title="Bài 1", 
            summary="Nội dung trùng lặp", 
            status="pending",
            metadata={"raw_document_id": str(self.raw_doc.id)}
        )

        mock_processor.process_and_index.return_value = True
        mock_processor.create_draft_chapters_from_raw.return_value = [c1, c2]

        process_document_task.run(self.raw_doc.id, self.group_id, self.user_id)

        c1.refresh_from_db()
        c2.refresh_from_db()

        # Chapter 1 hợp lệ -> Được khởi tạo qua Celery Chain Lớp 3
        mock_chain.assert_called_once()

        # Chapter 2 bị dính Lớp 1 -> Đánh dấu conflict_detected ngay
        self.assertEqual(c2.status, 'conflict_detected')
        self.assertTrue(c2.has_conflict)

    @patch('apps.ai_assistant.tasks.chain')
    @patch('apps.ai_assistant.tasks.DocumentProcessorService')
    def test_process_document_layer2_sql_check(self, mock_processor, mock_chain):
        """
        [Lớp 2] Thu thập ngữ cảnh trùng tiêu đề: Chương có tiêu đề trùng với chương cũ
        sẽ được ghi nhận thông tin vào metadata và VẪN tiếp tục chuyển sang Lớp 3 (AI).
        """
        KnowledgeChapter.objects.create(
            group_id=self.group_id, 
            title="Tiêu đề đã tồn tại", 
            summary="Mô tả cũ", 
            status="ready_to_approve"
        )

        new_c = KnowledgeChapter.objects.create(
            group_id=self.group_id,
            title="Tiêu đề đã tồn tại", 
            summary="Mô tả mới hoàn toàn", 
            status="pending",
            metadata={"raw_document_id": str(self.raw_doc.id)}
        )

        mock_processor.process_and_index.return_value = True
        mock_processor.create_draft_chapters_from_raw.return_value = [new_c]

        process_document_task.run(self.raw_doc.id, self.group_id, self.user_id)

        new_c.refresh_from_db()

        # Kiểm tra Lớp 3 VẪN ĐƯỢC KÍCH HOẠT qua Celery Chain:
        mock_chain.assert_called_once()
        
        # Kiểm tra thông tin ngữ cảnh đã được lưu vào metadata:
        self.assertIn("potential_conflicts", new_c.metadata)

    # ==========================================
    # 🧪 TEST CASES LỚP 3 (detect_semantic_overlap_task)
    # ==========================================

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
        
        # 🟢 Cập nhật: Thêm *args, **kwargs để nhận thêm các keyword argument như ai_config
        def mock_resolve(chapter, new_content, *args, **kwargs):
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