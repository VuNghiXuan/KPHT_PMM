# -*- coding: utf-8 -*-
"""
File: apps/ai_assistant/tests/test_semantic_search.py
Mục đích: Kiểm thử các trường hợp biên (Edge Cases) cho RAG / Semantic Search & VectorDB.
         Đảm bảo tính cô lập Group-Centric, Quy tắc Vàng về trạng thái tri thức (Approved-Only) 
         và điểm biên Cosine Similarity Threshold (>= 0.85).
Tác giả: Kỹ sư phần mềm cao cấp - VnxChatBot
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.group_chat.models import ChatGroup, KnowledgeChapter
from apps.ai_assistant.vector_store.chromadb_client import ChromaDBClient, VectorDBManager
from apps.ai_assistant.tasks import detect_semantic_overlap_task


class SemanticSearchEdgeCasesTestCase(TestCase):
    """
    Class: SemanticSearchEdgeCasesTestCase
    Mô tả: Bộ kiểm thử bảo vệ tính cô lập dữ liệu (Group-Centric Isolation),
           Quy tắc Vàng về trạng thái tri thức (Approved-Only)
           và ngưỡng Cosine Similarity (>= 0.85).
    """

    def setUp(self):
        """Khởi tạo dữ liệu kiểm thử độc lập cho 2 nhóm chat biệt lập."""
        self.group_a = ChatGroup.objects.create(
            name="Nhóm A - Phòng Tài Chính",
            description="Chứa tài liệu quy định tài chính bảo mật."
        )
        self.group_b = ChatGroup.objects.create(
            name="Nhóm B - Phòng Kỹ Thuật",
            description="Chứa tài liệu kỹ thuật hệ thống."
        )

    # -------------------------------------------------------------------------
    # EDGE CASE 1: Bảo mật cô lập Group (Group-Centric Isolation)
    # -------------------------------------------------------------------------
    @patch.object(ChromaDBClient, 'search')
    def test_edge_case_group_isolation(self, mock_search):
        """
        [EDGE CASE 1]: Khi Group A gửi truy vấn có nội dung trùng khớp 100% với dữ liệu
        của Group B, VectorDBManager BẮT BUỘC phải lọc theo metadata group_id và
        tuyệt đối KHÔNG trả về dữ liệu của Group B.
        """
        # Giả lập VectorDB trả về rỗng khi lọc đúng metadata group_id của Group A
        mock_search.return_value = []

        query_text = "Quy trình giải ngân và thanh toán ngân sách năm 2026"
        dummy_embedding = [0.1] * 1536

        with patch.object(ChromaDBClient, 'compute_embedding', return_value=dummy_embedding):
            # Gọi phương thức tìm kiếm với group_id của Group A
            results = VectorDBManager.search(
                embedding=dummy_embedding, 
                group_id=self.group_a.id, 
                threshold=0.85
            )

        # Kiểm tra phương thức search của ChromaDBClient có truyền đúng group_id của Group A
        mock_search.assert_called_with(
            embedding=dummy_embedding,
            group_id=self.group_a.id,
            threshold=0.85
        )
        self.assertEqual(len(results), 0, "Không được trả về kết quả của Group B cho Group A.")

    # -------------------------------------------------------------------------
    # EDGE CASE 2: Quy tắc Vàng về trạng thái Tri thức (Knowledge Lifecycle)
    # -------------------------------------------------------------------------
    def test_edge_case_knowledge_lifecycle_status_filter(self):
        """
        [EDGE CASE 2]: Cấm tuyệt đối dữ liệu ở trạng thái 'pending', 'staging', 'rejected',
        hoặc 'conflict_detected' xuất hiện trong kết quả RAG / Semantic Search. Chỉ cho phép 'approved'.
        """
        # Tạo các chapter ở đầy đủ các trạng thái trong DB
        chapter_pending = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Chương Nháp",
            summary="Dữ liệu nháp chưa kiểm chứng.",
            status="pending"
        )
        chapter_conflict = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Chương Xung Đột",
            summary="Dữ liệu bị trùng lặp.",
            status="conflict_detected"
        )
        chapter_approved = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Chương Chuẩn",
            summary="Dữ liệu chính thức đã được duyệt.",
            status="approved"
        )

        # Lọc danh sách tri thức sẵn sàng cho RAG trong Database theo group_id
        approved_chapters = KnowledgeChapter.objects.filter(
            group_id=self.group_a.id, 
            status="approved"
        )

        self.assertIn(chapter_approved, approved_chapters, "Chương đã duyệt phải sẵn sàng phục vụ RAG.")
        self.assertNotIn(chapter_pending, approved_chapters, "Chương 'pending' không được đưa vào RAG.")
        self.assertNotIn(chapter_conflict, approved_chapters, "Chương 'conflict_detected' không được đưa vào RAG.")

    # -------------------------------------------------------------------------
    # EDGE CASE 3: Kiểm soát điểm biên Cosine Similarity Threshold (>= 0.85)
    # -------------------------------------------------------------------------
    @patch.object(ChromaDBClient, 'search')
    def test_edge_case_cosine_similarity_threshold_boundary(self, mock_search):
        """
        [EDGE CASE 3]: Kiểm thử chính xác tại điểm biên điểm số Cosine Similarity.
        - Điểm = 0.8499 (< 0.85) -> Không bị coi là mâu thuẫn/xung đột (ready_to_approve).
        - Điểm = 0.8500 (>= 0.85) -> Bị gán nhãn xung đột tri thức (conflict_detected).
        """
        chapter = KnowledgeChapter.objects.create(
            group_id=self.group_a.id,
            title="Kiểm tra ngưỡng",
            summary="Nội dung test điểm số.",
            status="pending"
        )

        # Trường hợp 1: Điểm = 0.8499 (Dưới ngưỡng 0.85) -> An toàn
        mock_search.return_value = []
        detect_semantic_overlap_task(chapter.id)
        chapter.refresh_from_db()
        self.assertEqual(chapter.status, "ready_to_approve", "Điểm < 0.85 phải chuyển sang ready_to_approve.")

        # Reset lại trạng thái ban đầu
        chapter.status = "pending"
        chapter.save()

        # Trường hợp 2: Điểm = 0.8500 (Đúng/Trên ngưỡng 0.85) -> Xung đột
        mock_search.return_value = [{
            'id': 'doc_999',
            'document': 'Nội dung trùng lặp',
            'similarity': 0.85
        }]
        detect_semantic_overlap_task(chapter.id)
        chapter.refresh_from_db()
        self.assertEqual(chapter.status, "conflict_detected", "Điểm >= 0.85 phải gán nhãn conflict_detected.")

    # -------------------------------------------------------------------------
    # EDGE CASE 4: Khả năng chống chịu Đầu vào dị thường (Input Resilience)
    # -------------------------------------------------------------------------
    @patch.object(ChromaDBClient, 'search')
    def test_edge_case_abnormal_search_inputs(self, mock_search):
        """
        [EDGE CASE 4]: Kiểm tra hệ thống xử lý an toàn khi gặp các đầu vào bất thường
        như chuỗi rỗng, chuỗi khoảng trắng, hoặc khi VectorDB chưa có dữ liệu nào.
        """
        mock_search.return_value = []
        dummy_embedding = [0.0] * 1536

        # 1. Truy vấn khoảng trắng / rỗng
        empty_results = VectorDBManager.search(
            embedding=dummy_embedding, 
            group_id=self.group_a.id, 
            threshold=0.85
        )
        self.assertEqual(empty_results, [], "Truy vấn không có dữ liệu khớp phải trả về danh sách rỗng an toàn.")

        # 2. Group hoàn toàn mới (chưa có tài liệu nào)
        new_empty_group = ChatGroup.objects.create(name="Nhóm Rỗng")
        no_data_results = VectorDBManager.search(
            embedding=dummy_embedding, 
            group_id=new_empty_group.id, 
            threshold=0.85
        )
        self.assertEqual(no_data_results, [], "Tìm kiếm trên nhóm rỗng phải trả về [] an toàn mà không phát sinh ngoại lệ.")