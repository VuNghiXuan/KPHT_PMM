# -*- coding: utf-8 -*-
"""
Mục đích: Định nghĩa các đường dẫn URL cho phân hệ group_chat,
điều hướng các request đến các view chuyên biệt (Chat, Knowledge, Feedback, Member & AI).
Tuân thủ tuyệt đối quy tắc cô lập group_id.
"""

from django.urls import path
from apps.group_chat.views import (
    create_group,
    group_chat_detail,
    upload_document,
    delete_document_view,
    trigger_ai_learn_document_view,
    search_knowledge_view,
    knowledge_management,
    knowledge_action_view,
    promote_knowledge_view,
    rollback_knowledge,
    knowledge_chapter_list_view,
    approve_reject_chapter_view,
    knowledge_feedback_view,
    message_reactions_detail_view,
    add_member_to_group,
    update_ai_config_view,
    get_group_members_api,
    validate_and_test_ai_model,
    knowledge_dashboard_view,
    ConflictResolutionAPIView,
    ConflictChapterListAPIView,
    AIRewriteAPIView
)

app_name = 'group_chat'

urlpatterns = [
    # 💬 Quản lý phòng chat và nhóm (chat_views.py)
    path('create/', create_group, name='create_group'),
    path('<int:group_id>/', group_chat_detail, name='group_detail'),
    
    # 📁 Quản lý tài liệu và vòng đời tri thức (knowledge_document_views.py)
    path('<int:group_id>/upload/', upload_document, name='upload_document'),
    path('<int:group_id>/documents/<int:document_id>/learn/', trigger_ai_learn_document_view, name='trigger_ai_learn_document'),
    path('<int:group_id>/documents/<int:document_id>/reanalyze/', trigger_ai_learn_document_view, name='reanalyze_document'),
    path('<int:group_id>/documents/<int:document_id>/delete/', delete_document_view, name='delete_document'),



    # 🔍 API Tìm kiếm tri thức trong nhóm (Group-Centric Search API)
    path('<int:group_id>/knowledge/search/', search_knowledge_view, name='search_knowledge'),

    # 📊 Kho Tri Thức Nhóm & Dashboard Quản trị (Knowledge Dashboard)
    path('<int:group_id>/knowledge/', knowledge_dashboard_view, name='knowledge_dashboard'),
    path('<int:group_id>/knowledge/legacy/', knowledge_management, name='knowledge_management'),

    # 🔄 Quản lý vòng đời tri thức & Hành động phê duyệt (Pending / Approved / Rollback)
    path('<int:group_id>/knowledge/<int:knowledge_id>/<str:action>/', knowledge_action_view, name='knowledge_action'),
    path('<int:group_id>/knowledge/<int:pk>/rollback/', rollback_knowledge, name='knowledge_rollback'),
    path('message/<int:message_id>/promote-knowledge/', promote_knowledge_view, name='promote_knowledge'),

    # 🧠 Quản lý chương mục tri thức (Knowledge Chapters)
    path(
        '<int:group_id>/knowledge/chapters/', 
        knowledge_chapter_list_view, 
        name='knowledge_chapter_list'
    ),
    
    
    
    path(
        '<int:group_id>/knowledge/chapters/<int:chapter_id>/action/', 
        approve_reject_chapter_view, 
        name='approve_reject_chapter'
    ),

    # 🛡️ API Xử lý Xung đột Tri thức (Conflict Resolution)
    path(
            '<int:group_id>/knowledge/chapters/conflicts/', 
            ConflictChapterListAPIView.as_view(), 
            name='conflict_chapter_list_api'
        ),
        
    path(
            '<int:group_id>/knowledge/chapters/<int:chapter_id>/resolve/', 
            ConflictResolutionAPIView.as_view(), 
            name='conflict_resolution_api'  # Đã đồng bộ dấu gạch dưới (_) khớp với test case
        ),


  

    # 🛡️ API gọi AI viết lại nội dung sau tìm kiếm  
    # Trong urlpatterns:
    path(
        '<int:group_id>/knowledge/chapters/<int:chapter_id>/rewrite/', 
        AIRewriteAPIView.as_view(), 
        name='ai_rewrite'
    ),



    # ❤️ Quản lý tương tác cảm xúc và Feedback Loop (feedback_views.py)
    path('message/<int:message_id>/feedback/', knowledge_feedback_view, name='knowledge_feedback'),
    path('message/<int:message_id>/reactions-detail/', message_reactions_detail_view, name='message_reactions_detail'),

    # 🤖 Quản lý thành viên và cấu hình AI riêng biệt theo nhóm (member_ai_views.py)
    path('<int:group_id>/add-member/', add_member_to_group, name='add_member_to_group'),
    path('<int:group_id>/ai-config/', update_ai_config_view, name='update_ai_config'),
    path('<uuid:group_id>/members-api/', get_group_members_api, name='get_group_members_api'),
    path('<int:group_id>/ai-config/validate/', validate_and_test_ai_model, name='validate_ai_config'),
]