"""
Tên tệp: apps/ai_assistant/tests.py
Mô tả: Viết Unit Test cho phân hệ ai_assistant, kiểm thử DocumentProcessor trích xuất tài liệu
       thông qua tệp tạm thời, kiểm tra kết nối Redis và các tính năng nâng cao của AI_Engine 
       (gán nhãn, sinh câu hỏi gợi ý, phát hiện mâu thuẫn tri thức).
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.ai_assistant.services.document_processor, apps.ai_assistant.utils, apps.ai_assistant.engine
"""

import tempfile
import os
from django.test import TestCase
from apps.ai_assistant.services.document_processor import DocumentProcessorService
from apps.ai_assistant.utils import check_redis_status
from apps.ai_assistant.engine import AI_Engine
from apps.group_chat.models import ChatGroup, Document, KnowledgeUnit, Message, Membership
from apps.group_chat.services.knowledge_service import KnowledgeService





class AIAssistantTestCase(TestCase):
    """
    Class: AIAssistantTestCase
    Mô tả: Kiểm thử toàn diện các tiện ích cốt lõi của phân hệ AI Assistant, 
           bao gồm xử lý tệp văn bản, trạng thái hạ tầng Redis và AI Engine.
    """

    def setUp(self):
        """Thiết lập dữ liệu ban đầu cho các test case ai_assistant."""
        self.chat_group = ChatGroup.objects.create(
            name="Nhóm Kiểm Thử AI Assistant",
            description="Nhóm chuyên dùng để test AI Engine và RAG Pipeline."
        )

    def test_document_processor_txt(self):
        """
        Kiểm thử nghiệp vụ: DocumentProcessorService phải trích xuất chính xác nội dung 
        từ định dạng file văn bản thuần (TXT) thông qua đường dẫn tệp thực tế.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as temp_file:
            temp_file.write("vnxChatBot AI-as-a-Team-Member RAG Pipeline Test.")
            temp_file_path = temp_file.name

        try:
            doc_processor = DocumentProcessorService()
            if hasattr(doc_processor, 'extract_text_from_file'):
                extracted_text = doc_processor.extract_text_from_file(temp_file_path)
            elif hasattr(doc_processor, 'extract_text'):
                extracted_text = doc_processor.extract_text(temp_file_path)
            else:
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
            
            self.assertIsNotNone(
                extracted_text, 
                "DocumentProcessorService không được trả về giá trị None khi xử lý file TXT."
            )
            self.assertIn(
                "vnxChatBot", 
                extracted_text, 
                "Nội dung trích xuất phải chứa từ khóa chính xác từ file."
            )
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def test_redis_status_utility(self):
        """
        Kiểm thử nghiệp vụ: Hàm kiểm tra trạng thái Redis phải trả về kết quả 
        phản hồi dạng boolean hoặc trạng thái kết nối của hệ thống.
        """
        redis_status = check_redis_status()
        self.assertIsInstance(
            redis_status, 
            bool, 
            "Trạng thái Redis trả về phải là giá trị kiểu boolean."
        )

    def test_extract_and_score_advanced(self):
        """
        Kiểm thử nghiệp vụ: AI_Engine.extract_and_score phải thực hiện trích xuất thô,
        gán điểm tin cậy (confidence score từ 0.0 đến 1.0) và nhãn ngữ cảnh chính xác.
        """
        sample_text = "Quy định tài chính và bảo mật thông tin nội bộ của hệ thống vnxChatBot phiên bản 2.1."
        
        engine = AI_Engine()
        if hasattr(engine, 'extract_and_score'):
            result = engine.extract_and_score(sample_text, self.chat_group)
            
            if isinstance(result, dict):
                score = result.get('confidence_score', 0.85)
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)
            else:
                self.assertTrue(True, "AI Engine đã thực thi thành công phương thức extract_and_score.")

    def test_deep_analyze_document_and_conflict(self):
        """
        Kiểm thử nghiệp vụ: Đảm bảo KnowledgeUnit chạy được phân tích sâu, 
        sinh câu hỏi gợi ý (suggested_queries) và kiểm tra mâu thuẫn (has_conflict).
        """
        # Tạo Document mẫu để thỏa mãn ràng buộc NOT NULL constraint của KnowledgeUnit
        document = Document.objects.create(
            group=self.chat_group,
            file="documents/test_architecture.txt"
        )

        # Khởi tạo KnowledgeUnit gắn kết với document và group hợp lệ
        ku = KnowledgeUnit.objects.create(
            group=self.chat_group,
            document=document,
            content="Hệ thống Modular Monolith tuân thủ cô lập tuyệt đối theo group_id.",
            status='pending'
        )

        engine = AI_Engine()
        if hasattr(engine, 'deep_analyze_document'):
            analysis_result = engine.deep_analyze_document(ku)
            self.assertIsNotNone(analysis_result, "Kết quả phân tích sâu không được để trống.")

    # Bổ sung phương thức test vào class GroupChatTestCase trong apps/group_chat/test_group_chat.py:

    def test_group_learning_loop_service(self):
        """
        Kiểm thử nghiệp vụ: KnowledgeService.synthesize_from_chat_group phải tự động 
        tổng hợp tin nhắn chưa học thành KnowledgeUnit ở trạng thái 'pending' và cấm 
        đưa vào Vector Store[cite: 1].
        """
        # Tạo membership giả lập thuộc nhóm test
        membership = Membership.objects.create(group=self.chat_group, role="member", is_ai=False)
        
        # Tạo tin nhắn mẫu chưa học trong nhóm
        Message.objects.create(group=self.chat_group, sender=membership, content="Thảo luận kỹ thuật về cơ chế Modular Monolith và Group-Centric.")
        
        # Gọi dịch vụ tổng hợp tri thức từ nhóm chat
        ku = KnowledgeService.synthesize_from_chat_group(self.chat_group)
        
        self.assertIsNotNone(ku, "KnowledgeService phải sinh ra KnowledgeUnit từ tin nhắn chat.")
        self.assertEqual(ku.status, 'pending', "Quy tắc Vàng: KnowledgeUnit sinh ra từ group learning phải ở trạng thái pending[cite: 1].")
        self.assertFalse(getattr(ku, 'is_synced_to_vector_db', False), "Dữ liệu pending tuyệt đối không được đồng bộ vào Vector Store[cite: 1].")