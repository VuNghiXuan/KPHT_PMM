"""
File: apps/group_chat/admin.py
Mục đích: Cấu hình giao diện quản trị Django Admin cho các thực thể thuộc phân hệ Group-Centric 
          bao gồm ChatGroup, Membership, Document và KnowledgeUnit.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models
"""
from django.contrib import admin
from .models import ChatGroup, Membership, Document, KnowledgeUnit

@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    """
    Class: ChatGroupAdmin
    Description: Quản lý hiển thị danh sách các nhóm làm việc (tenant isolation) trên Django Admin.
    """
    list_display = ('name', 'plan_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'plan_type')
    search_fields = ('name',)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Class: MembershipAdmin
    Description: Quản lý mối quan hệ giữa User và ChatGroup, theo dõi vai trò thành viên hoặc AI.
    """
    # Khắc phục lỗi: Thay thế 'joined_at' bằng các trường hợp lệ của model Membership
    list_display = ('user', 'group', 'role')
    list_filter = ('role', 'group')
    search_fields = ('user__username', 'group__name')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Class: DocumentAdmin
    Description: Quản lý các tài liệu được tải lên theo từng nhóm phục vụ hệ thống RAG.
    """
    list_display = ('file', 'group', 'uploaded_by', 'uploaded_at')
    list_filter = ('group', 'uploaded_at')

@admin.register(KnowledgeUnit)
class KnowledgeUnitAdmin(admin.ModelAdmin):
    """
    Class: KnowledgeUnitAdmin
    Description: Quản lý vòng đời tri thức (Knowledge Lifecycle) từ trạng thái pending sang approved hoặc rollback.
    """
    list_display = ('entity_name', 'group', 'status', 'context_tag') 
    list_filter = ('status', 'group')
    list_editable = ('status',)
    search_fields = ('entity_name', 'context_tag')