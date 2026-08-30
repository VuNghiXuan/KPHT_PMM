# -*- coding: utf-8 -*-
"""
Mục đích: Gom và export lại toàn bộ view của phân hệ group_chat để urls.py gọi bình thường.
"""
from .conflict_views import (
    ConflictResolutionAPIView
)

from .conflict_chapter_listAPIView import (
    ConflictChapterListAPIView
)

from .chat_views import (
    create_group,
    group_chat_detail,
)
from .knowledge_document_views import (
    upload_document,
    delete_document_view,
    trigger_ai_learn_document_view,
    search_knowledge_view,
)
from .knowledge_lifecycle_views import (
    knowledge_management,
    knowledge_action_view,
    promote_knowledge_view,
    rollback_knowledge,
    knowledge_chapter_list_view,
    approve_reject_chapter_view,
    knowledge_dashboard_view,
)

from .feedback_views import (
    knowledge_feedback_view,
    message_reactions_detail_view,
    handle_message_feedback_ajax,
)
from .member_ai_views import (
    add_member_to_group,
    get_group_members_api,
    update_ai_config_view,
    validate_and_test_ai_model,
)
from .ai_action_serializer import (AIRewriteAPIView
)