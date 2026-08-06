# File: apps/group_chat/views/__init__.py
"""
Mục đích: Gom và export lại toàn bộ view của phân hệ group_chat để urls.py gọi bình thường.
"""

from .chat_views import (
    create_group,
    group_chat_detail,
)
from .knowledge_views import (
    upload_document,
    knowledge_management,
    knowledge_action_view,
    trigger_ai_learn_document_view,
    promote_knowledge_view,
    rollback_knowledge,
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
)