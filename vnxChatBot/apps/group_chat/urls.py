


# from django.urls import path
# from . import views

# app_name = 'group_chat'



# urlpatterns = [
#     path('create/', views.create_group, name='create_group'),
#     path('<int:group_id>/', views.group_chat_detail, name='group_detail'),
#     path('<int:group_id>/upload/', views.upload_document, name='upload_document'),
#     path('<int:group_id>/add-member/', views.add_member_to_group, name='add_member_to_group'),
    
#     # 🧠 Quản lý vòng đời tri thức và Feedback Loop qua message_id
#     path('message/<int:message_id>/feedback/', views.knowledge_feedback_view, name='knowledge_feedback'),
    
#     # 🔍 Sửa lại đường dẫn này (bỏ chữ 'groups/' ở đầu)
#     path('message/<int:message_id>/reactions-detail/', views.message_reactions_detail_view, name='message_reactions_detail'),
#     path('message/<int:message_id>/promote-knowledge/', views.promote_knowledge_view, name='promote_knowledge'),

    
#     # 🧠 Quản lý tri thức theo group_id
#     path('<int:group_id>/knowledge/', views.knowledge_management, name='knowledge_management'),
#     path('knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
#     path('document/<int:doc_id>/delete/', views.rollback_knowledge, name='delete_document'),
    
#     # 🤖 Cấu hình AI riêng cho nhóm (Group-Centric AI Configuration)
#     path('<int:group_id>/ai-config/', views.update_ai_config_view, name='update_ai_config'),
#     path('<uuid:group_id>/members-api/', views.get_group_members_api, name='get_group_members_api'),
#     # path('groups/<uuid:group_id>/members-api/', views.get_group_members_api, name='get_group_members_api'),
# ]


# File: apps/group_chat/urls.py
# File: apps/group_chat/urls.py
"""
Mục đích: Định nghĩa các đường dẫn URL cho phân hệ group_chat,
điều hướng các request đến các view chuyên biệt (Chat, Knowledge, Feedback, Member & AI).
"""

from django.urls import path
from . import views

app_name = 'group_chat'

urlpatterns = [
    # 💬 Quản lý phòng chat và nhóm (chat_views.py)
    path('create/', views.create_group, name='create_group'),
    path('<int:group_id>/', views.group_chat_detail, name='group_detail'),
    
    # 📁 Quản lý tài liệu và vòng đời tri thức (knowledge_views.py)
    path('<int:group_id>/upload/', views.upload_document, name='upload_document'),
    path('<int:group_id>/knowledge/', views.knowledge_management, name='knowledge_management'),
    # path('knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
    path('documents/<int:document_id>/learn/', views.trigger_ai_learn_document_view, name='trigger_ai_learn_document'),
    # path('document/<int:doc_id>/delete/', views.rollback_knowledge, name='delete_document'),
    path('groups/<int:group_id>/knowledge/<int:pk>/rollback/', views.rollback_knowledge, name='knowledge_rollback'),

    
    path('<int:group_id>/knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
    path('groups/<int:group_id>/knowledge/<int:pk>/rollback/', views.rollback_knowledge, name='knowledge_rollback'),

    path('message/<int:message_id>/promote-knowledge/', views.promote_knowledge_view, name='promote_knowledge'),


    

    # ❤️ Quản lý tương tác cảm xúc và Feedback Loop (feedback_views.py)
    path('message/<int:message_id>/feedback/', views.knowledge_feedback_view, name='knowledge_feedback'),
    path('message/<int:message_id>/reactions-detail/', views.message_reactions_detail_view, name='message_reactions_detail'),

    # 🤖 Quản lý thành viên và cấu hình AI riêng biệt theo nhóm (member_ai_views.py)
    path('<int:group_id>/add-member/', views.add_member_to_group, name='add_member_to_group'),
    path('<int:group_id>/ai-config/', views.update_ai_config_view, name='update_ai_config'),
    path('<uuid:group_id>/members-api/', views.get_group_members_api, name='get_group_members_api'),

    
]