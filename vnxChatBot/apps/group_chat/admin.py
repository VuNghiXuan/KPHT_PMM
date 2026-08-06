"""
File: apps/group_chat/admin.py
Mục đích: Cấu hình giao diện quản trị Django Admin cho các thực thể thuộc phân hệ Group-Centric 
          bao gồm ChatGroup, Membership, Document, KnowledgeUnit và Message.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models
"""
from django.contrib import admin
from .models import ChatGroup, Membership, Document, KnowledgeUnit, Message

@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    """
    Class: ChatGroupAdmin
    Description: Quản lý hiển thị danh sách các nhóm làm việc (tenant isolation) trên Django Admin.
    """
    list_display = ('name', 'plan_type', 'ai_model', 'is_active', 'created_at')
    list_filter = ('is_active', 'plan_type', 'ai_model')
    search_fields = ('name', 'description')

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Class: MembershipAdmin
    Description: Quản lý mối quan hệ giữa User và ChatGroup, theo dõi vai trò thành viên hoặc AI.
    """
    list_display = ('user', 'group', 'role', 'is_ai')
    list_filter = ('role', 'is_ai', 'group')
    search_fields = ('user__username', 'group__name')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Class: DocumentAdmin
    Description: Quản lý các tài liệu được tải lên theo từng nhóm phục vụ hệ thống RAG.
    """
    list_display = ('file', 'group', 'uploaded_by', 'upload_type', 'uploaded_at')
    list_filter = ('group', 'upload_type', 'uploaded_at')
    search_fields = ('file', 'uploaded_by__username')

@admin.register(KnowledgeUnit)
class KnowledgeUnitAdmin(admin.ModelAdmin):
    """
    Class: KnowledgeUnitAdmin
    Description: Quản lý vòng đời tri thức (Knowledge Lifecycle) từ trạng thái pending sang approved hoặc rollback.
    """
    list_display = ('entity_name', 'group', 'status', 'context_tag') 
    list_filter = ('status', 'group')
    list_editable = ('status',)
    search_fields = ('entity_name', 'context_tag', 'content')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Class: MessageAdmin
    Description: Quản lý toàn bộ trao đổi tin nhắn, tệp đính kèm và ngữ cảnh phản hồi trong nhóm chat.
    """
    list_display = ('id', 'group', 'sender', 'content_preview', 'document', 'created_at')
    list_filter = ('group', 'created_at')
    search_fields = ('content', 'sender__user__username')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        """Hiển thị tóm tắt nội dung tin nhắn trên bảng quản trị admin."""
        return obj.content[:50] + "..." if obj.content and len(obj.content) > 50 else obj.content
    content_preview.short_description = "Nội dung tóm tắt"