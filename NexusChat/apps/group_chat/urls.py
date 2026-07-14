# apps/group_chat/urls.py
from django.urls import path
from . import views

app_name = 'group_chat' 

urlpatterns = [
    path('<int:group_id>/', views.group_chat_detail, name='detail'),
    path('<int:group_id>/upload/', views.upload_document, name='upload'), # Đổi tên thành 'upload'
]