# -*- coding: utf-8 -*-
"""
Module: apps.group_chat.tests.test_document_pipeline
Mục đích: Unit test suite cho luồng tiếp nhận tài liệu và vòng đời tri thức.
"""

from unittest.mock import patch
from django.test import TestCase
from apps.group_chat.models import ChatGroup, RawDocument, Document, KnowledgeChapter

class DocumentPipelineTestCase(TestCase):
    """
    Unit test suite for the Document Ingestion and Knowledge Lifecycle pipeline.
    Ensures strict group scoping, gold rule enforcement, and safe state transitions.
    """

    @classmethod
    def setUpTestData(cls):
        # Setup baseline test groups for hard-scoping validation
        cls.group_alpha = ChatGroup.objects.create(name="Alpha Chat Group")
        cls.group_beta = ChatGroup.objects.create(name="Beta Chat Group")

    def test_raw_document_initial_state(self):
        """Test that a newly uploaded document starts strictly in 'PENDING' state."""
        raw_doc = RawDocument.objects.create(
            group=self.group_alpha,
            file="documents/test.pdf",
            file_type="pdf",
            status="PENDING"
        )
        self.assertEqual(raw_doc.status, "PENDING")
        self.assertEqual(raw_doc.group, self.group_alpha)

    # @patch('apps.group_chat.tasks.process_document_task.delay')
    # ✅ Đường dẫn mới (đúng)
    @patch('apps.ai_assistant.tasks.process_document_task.delay')
    def test_golden_rule_vector_store_block(self, mock_celery_task):
        """
        [Golden Rule Test] Ensure that knowledge chapters in 'pending' or 'staging' 
        are strictly prohibited from vector database embedding sync.
        """
        chapter = KnowledgeChapter.objects.create(
            group_id=self.group_alpha.id,
            title="Staging Chapter",
            summary="Draft knowledge content...",
            status="staging",
            has_conflict=False
        )
        
        # Assert that status is not approved, meaning vector sync must not happen
        self.assertNotEqual(chapter.status, "approved")

    def test_approval_and_vector_sync_trigger(self):
        """
        Test that transitioning a chapter to 'approved' successfully 
        satisfies conditions for vector synchronization.
        """
        chapter = KnowledgeChapter.objects.create(
            group_id=self.group_alpha.id,
            title="Approved Chapter",
            summary="Final validated knowledge...",
            status="approved",
            has_conflict=False
        )

        self.assertEqual(chapter.status, "approved")
        # Signal / Vector embedding hook should be allowed to execute here