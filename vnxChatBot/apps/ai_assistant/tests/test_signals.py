"""
Mục đích: Kiểm tra Signal của ai_assistant không bị trigger trùng lặp.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.test import TestCase
from unittest.mock import patch
from apps.group_chat.models import ChatGroup, Document, KnowledgeUnit

class KnowledgeSignalTest(TestCase):
    def setUp(self):
        self.group = ChatGroup.objects.create(name="Nhóm Test")
        self.doc = Document.objects.create(group=self.group, file="test.pdf")

    @patch('apps.ai_assistant.services.rag_engine.RAGEngine.add_knowledge')
    def test_signal_triggers_on_approval(self, mock_add):
        """
        Kiểm tra: Khi KnowledgeUnit chuyển sang 'approved', 
        RAGEngine.add_knowledge phải được gọi đúng 1 lần.
        """
        unit = KnowledgeUnit.objects.create(
            document=self.doc, 
            status='pending',
            entity_name="Vàng 24k"
        )
        
        # Chuyển trạng thái sang approved
        unit.status = 'approved'
        unit.save()
        
        # Xác nhận RAGEngine được gọi
        mock_add.assert_called_once()
        print("PASS: Signal handle_knowledge_approval hoạt động đúng, không trùng lặp.")