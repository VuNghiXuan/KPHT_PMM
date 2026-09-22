# -*- coding: utf-8 -*-
# Path: apps/group_chat/tests/test_knowledge_signals.py
# Description: Unit test kiểm thử vòng đời KnowledgeChapter và cơ chế đồng bộ VectorDB qua Signals.

from unittest.mock import patch
from django.test import TransactionTestCase
from django.core.cache import cache
from apps.group_chat.models import ChatGroup, KnowledgeChapter

class TestKnowledgeChapterSignal(TransactionTestCase):
    def setUp(self):
        # 🧹 Xóa sạch cache Redis trước mỗi test để tránh kẹt cache_key
        cache.clear()
        
        self.group = ChatGroup.objects.create(name="Nhóm Test Signal")
        self.chapter = KnowledgeChapter.objects.create(
            group_id=self.group.id,
            title="Tài liệu kiểm thử signal",
            status="pending"
        )

    @patch('apps.ai_assistant.signals.sync_chapter_to_vector_async')
    def test_approved_chapter_triggers_vector_sync(self, mock_sync_async):
        # 📌 1. Chuyển trạng thái sang approved để kích hoạt signal post_save
        self.chapter.status = 'approved'
        self.chapter.save()
        
        # 🚀 2. Xác thực Celery task được gọi qua phương thức .delay() với đúng định dạng group_id và chapter_id
        mock_sync_async.delay.assert_called_once_with(str(self.group.id), self.chapter.id)

    @patch('apps.ai_assistant.signals.sync_chapter_to_vector_async')
    def test_pending_chapter_does_not_sync(self, mock_sync_async):
        # 📌 1. Lưu lại bản ghi khi vẫn duy trì ở trạng thái pending
        self.chapter.summary = "Cập nhật tóm tắt nháp"
        self.chapter.save()
        
        # 🛡️ 2. Xác nhận hàm đồng bộ tuyệt đối không bị gọi để tuân thủ Nguyên tắc Vàng
        mock_sync_async.delay.assert_not_called()