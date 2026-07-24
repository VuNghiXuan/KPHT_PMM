# from django.urls import path
# from . import views

# app_name = 'group_chat'

# urlpatterns = [
#     path('create/', views.create_group, name='create_group'),
#     path('<int:group_id>/', views.group_chat_detail, name='chat_detail'),
#     path('<int:group_id>/upload/', views.upload_document, name='upload_document'),
#     path('<int:group_id>/add-member/', views.add_member_to_group, name='add_member_to_group'),
#     path('message/<int:message_id>/feedback/', views.knowledge_feedback_view, name='knowledge_feedback'),
    
#     # 🧠 Sửa lại đường dẫn quản lý tri thức theo group_id cho phù hợp với nút bấm ở Sidebar/Offcanvas
#     path('<int:group_id>/knowledge/', views.knowledge_management, name='knowledge_management'),
    
#     # Đường dẫn xử lý hành động cụ thể trên từng KnowledgeUnit
#     path('knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
    
#     path('document/<int:doc_id>/delete/', views.rollback_knowledge, name='delete_document'),
#     path('<int:group_id>/ai-config/', views.update_ai_config, name='update_ai_config'),
# ]


from django.urls import path
from . import views

app_name = 'group_chat'

urlpatterns = [
    path('create/', views.create_group, name='create_group'),
    path('<int:group_id>/', views.group_chat_detail, name='chat_detail'), # <--- Tên route là chat_detail
    path('<int:group_id>/upload/', views.upload_document, name='upload_document'),
    path('<int:group_id>/add-member/', views.add_member_to_group, name='add_member_to_group'),
    path('message/<int:message_id>/feedback/', views.knowledge_feedback_view, name='knowledge_feedback'),
    
    # 🧠 Quản lý tri thức theo group_id
    path('<int:group_id>/knowledge/', views.knowledge_management, name='knowledge_management'),
    
    # Đường dẫn xử lý hành động cụ thể trên từng KnowledgeUnit
    path('knowledge/<int:knowledge_id>/<str:action>/', views.knowledge_action_view, name='knowledge_action'),
    
    path('document/<int:doc_id>/delete/', views.rollback_knowledge, name='delete_document'),
    
    # 🤖 Đồng bộ tên route thành update_ai_config để khớp với view update_ai_config_view
    path('<int:group_id>/ai-config/', views.update_ai_config_view, name='update_ai_config'),
]
