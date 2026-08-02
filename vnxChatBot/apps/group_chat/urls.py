


from django.urls import path
from . import views

app_name = 'group_chat'


urlpatterns = [
    path('create/', views.create_group, name='create_group'),
    path('<int:group_id>/', views.group_chat_detail, name='chat_detail'),
    path('<int:group_id>/upload/', views.upload_document, name='upload_document'),
    path('<int:group_id>/add-member/', views.add_member_to_group, name='add_member_to_group'),
    
    # path('<uuid:group_id>/add-member/', views.add_member_to_group, name='add_member_to_group'),
    path('message/<int:message_id>/feedback/', views.knowledge_feedback_view, name='knowledge_feedback'),
    
    # 🧠 Quản lý tri thức theo group_id
    path('<int:group_id>/knowledge/', views.knowledge_management, name='knowledge_management'),
    path('knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
    path('document/<int:doc_id>/delete/', views.rollback_knowledge, name='delete_document'),
    
    # 🤖 Cấu hình AI riêng cho nhóm (Group-Centric AI Configuration)
    path('<int:group_id>/ai-config/', views.update_ai_config_view, name='update_ai_config'),
    
]