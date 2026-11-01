"""
File: apps/group_chat/admin.py
Mục đích: Cấu hình giao diện quản trị Django Admin cho các thực thể thuộc phân hệ Group-Centric 
         bao gồm ChatGroup, Membership, GroupMember, Document, RawDocument, 
         BusinessGlossary, KnowledgeUnit, KnowledgeChapter, KnowledgeTree, và Message.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models
"""
from django.contrib import admin
from .models import (
    ChatGroup, Membership, GroupMember,
    Document, RawDocument,
    BusinessGlossary, KnowledgeUnit, KnowledgeChapter, KnowledgeTree,
    Message, MessageFeedback, ConflictResolutionLog
)

@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    """
    Class: ChatGroupAdmin
    Description: Quản lý hiển thị danh sách các nhóm làm việc (tenant isolation) trên Django Admin.
    """
    list_display = ('name', 'plan_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'plan_type')
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

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    """
    Class: GroupMemberAdmin
    Description: Quản lý quyền phê duyệt tri thức nội bộ và public của thành viên trong nhóm.
    """
    list_display = ('user', 'group', 'role', 'can_approve_internal', 'can_approve_public')
    list_filter = ('role', 'can_approve_internal', 'can_approve_public')
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

@admin.register(RawDocument)
class RawDocumentAdmin(admin.ModelAdmin):
    """
    Class: RawDocumentAdmin
    Description: Quản lý tài liệu vật lý thô đóng vai trò Source of Truth cho luồng Audit.
    """
    list_display = ('id', 'group', 'file_type', 'status', 'created_at')
    list_filter = ('status', 'file_type', 'group')
    search_fields = ('file', 'group__name')

@admin.register(BusinessGlossary)
class BusinessGlossaryAdmin(admin.ModelAdmin):
    """
    Class: BusinessGlossaryAdmin
    Description: Quản lý từ điển nghiệp vụ giúp giải quyết từ đa nghĩa và đồng nghĩa theo nhóm.
    """
    list_display = ('term', 'context_tag', 'group', 'created_at')
    list_filter = ('context_tag', 'group')
    search_fields = ('term', 'context_tag', 'description')

@admin.register(KnowledgeUnit)
class KnowledgeUnitAdmin(admin.ModelAdmin):
    """
    Class: KnowledgeUnitAdmin
    Description: Quản lý vòng đời tri thức (Knowledge Lifecycle) từ trạng thái pending sang approved hoặc rollback.
    """
    list_display = ('entity_name', 'group', 'status', 'context_tag', 'confidence_score', 'is_conflict') 
    list_filter = ('status', 'is_conflict', 'group')
    list_editable = ('status',)
    search_fields = ('entity_name', 'context_tag', 'content')

@admin.register(KnowledgeChapter)
class KnowledgeChapterAdmin(admin.ModelAdmin):
    """
    Class: KnowledgeChapterAdmin
    Description: Quản lý phân cấp chương tri thức theo nhóm, kiểm soát vòng đời và trạng thái mâu thuẫn.
    """
    list_display = ('title', 'group_id', 'parent', 'status', 'has_conflict', 'version')
    list_filter = ('status', 'has_conflict')
    list_editable = ('status', 'has_conflict')
    search_fields = ('title', 'summary')
    readonly_fields = ('version',)

@admin.register(KnowledgeTree)
class KnowledgeTreeAdmin(admin.ModelAdmin):
    """
    Class: KnowledgeTreeAdmin
    Description: Quản lý cấu trúc cây tri thức đã qua kiểm định làm nguồn dữ liệu chính cho Vector Store.
    """
    list_display = ('id', 'group', 'source_doc', 'confidence_score', 'is_active')
    list_filter = ('is_active', 'group')
    list_editable = ('is_active',)
    search_fields = ('group__name',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Class: MessageAdmin
    Description: Quản lý toàn bộ trao đổi tin nhắn, tệp đính kèm và ngữ cảnh phản hồi trong nhóm chat.
    """
    list_display = ('id', 'group', 'sender', 'content_preview', 'is_learned', 'document', 'created_at')
    list_filter = ('group', 'is_learned', 'created_at')
    search_fields = ('content', 'sender__user__username')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        """Hiển thị tóm tắt nội dung tin nhắn trên bảng quản trị admin."""
        return obj.content[:50] + "..." if obj.content and len(obj.content) > 50 else obj.content
    content_preview.short_description = "Nội dung tóm tắt"

@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    """
    Class: MessageFeedbackAdmin
    Description: Quản lý phản hồi đánh giá tin nhắn từ người dùng phục vụ fine-tuning.
    """
    list_display = ('id', 'group', 'message', 'user', 'type', 'created_at')
    list_filter = ('type', 'group')
    search_fields = ('comment', 'user__username')

@admin.register(ConflictResolutionLog)
class ConflictResolutionLogAdmin(admin.ModelAdmin):
    """
    Class: ConflictResolutionLogAdmin
    Mô tả: Quản lý lịch sử xung đột tri thức, hiển thị trạng thái xử lý 
          và hỗ trợ kiểm toán vòng đời dữ liệu Human-in-the-Loop trên Django Admin.
    """
    list_display = ('id', 'group', 'knowledge_unit', 'status', 'created_at', 'resolved_at')
    list_filter = ('status', 'group', 'created_at')
    search_fields = ('conflict_reason', 'group__name', 'knowledge_unit__entity_name')
    readonly_fields = ('created_at', 'resolved_at', 'original_content', 'conflicting_content')
    list_editable = ('status',)