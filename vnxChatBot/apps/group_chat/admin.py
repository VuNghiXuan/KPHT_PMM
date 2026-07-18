from django.contrib import admin
from .models import ChatGroup, Membership, Document, KnowledgeUnit

@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'plan_type')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file', 'group', 'uploaded_at')
    list_filter = ('group',)

@admin.register(KnowledgeUnit)
class KnowledgeUnitAdmin(admin.ModelAdmin):
    list_display = ('entity_name', 'group', 'status', 'context_tag') # Đảm bảo field 'group' tồn tại trong model
    list_filter = ('status', 'group')
    list_editable = ('status',)