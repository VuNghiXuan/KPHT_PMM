from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from .models import DataType, ProjectStructure, IntentManagement, IntentLog


@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_ai_generated', 'confidence_score')
    search_fields = ('name', 'code')
    list_filter = ('is_ai_generated',)

@admin.register(ProjectStructure)
class ProjectStructureAdmin(admin.ModelAdmin):
    # Hiển thị cấu trúc dạng cây trực quan
    list_display = ('tree_display', 'obj_type', 'path', 'is_active')
    list_filter = ('obj_type', 'is_active', 'level')
    search_fields = ('name', 'path', 'docstring')
    ordering = ('path',)
    
    change_list_template = "admin/project_structure_changelist.html"

    def tree_display(self, obj):
        """Tạo hiệu ứng nhánh cây bằng ký tự chuyên nghiệp"""
        padding = obj.level * 20
        # Ký tự nối nhánh
        prefix = "└─ " if obj.level > 0 else ""
        
        # Icon đại diện
        icons = {'FILE': '📄', 'CLASS': '📦', 'FUNC': '⚡'}
        icon = icons.get(obj.obj_type, '🔹')
        
        # Định dạng màu sắc theo loại
        colors = {'FILE': '#2c3e50', 'CLASS': '#e67e22', 'FUNC': '#2980b9'}
        color = colors.get(obj.obj_type, '#444')
        weight = "bold" if obj.obj_type != 'FUNC' else "normal"

        return format_html(
            '<span style="margin-left:{}px; color:{}; font-weight:{}">{} {} {}</span>',
            padding, color, weight, prefix, icon, obj.name
        )
    tree_display.short_description = "Cấu trúc hệ thống"

    # --- LOGIC ĐỒNG BỘ MÃ NGUỒN ---
    def get_urls(self):
        urls = super().get_urls()
        return [path('sync-code/', self.admin_site.admin_view(self.sync_view), name='sync-code-structure')] + urls

    def sync_view(self, request):
        try:
            msg = ProjectStructure.sync_project_structure()
            self.message_user(request, msg, messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Lỗi quét code: {str(e)}", messages.ERROR)
        return redirect("..")

@admin.register(IntentManagement)
class IntentManagementAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'intent_code', 'handler_func', 'hit_count', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('display_name', 'intent_code', 'keywords')
    
    # Chỉ chọn các Hàm (Function) trong ProjectStructure để mapping
    autocomplete_fields = ('handler_func',) 

    fieldsets = (
        ('Định danh & Điều hướng', {
            'fields': ('display_name', 'intent_code', 'handler_func', 'knowledge_type')
        }),
        ('Cấu hình nhận diện', {
            'fields': ('keywords', 'is_active'),
            'description': 'AI sẽ dùng keywords này để định tuyến câu hỏi.'
        }),
        ('Thống kê', {
            'fields': ('hit_count',),
        }),
    )
    readonly_fields = ('hit_count',)

@admin.register(IntentLog)
class IntentLogAdmin(admin.ModelAdmin):
    """Nơi anh Vũ thực hiện RLHF: Chỉnh sửa tư duy AI"""
    list_display = ('id', 'intent', 'short_query', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'intent', 'created_at')
    list_editable = ('is_correct',)
    search_fields = ('query_text', 'feedback_note')
    
    readonly_fields = ('query_text', 'ai_response_logic', 'created_at')

    def short_query(self, obj):
        return obj.query_text[:50] + "..." if len(obj.query_text) > 50 else obj.query_text
    short_query.short_description = "Câu hỏi khách"

    def save_model(self, request, obj, form, change):
        """Ghi chú: Nếu anh sửa feedback, sau này AI sẽ lấy dữ liệu này để học tập"""
        if obj.is_correct is False and not obj.feedback_note:
            messages.warning(request, "Anh Vũ ơi, anh đánh dấu AI sai thì nên ghi thêm chú thích ở Feedback để nó sửa nhé!")
        super().save_model(request, obj, form, change)

# @admin.register(KnowledgeExchange)
# class KnowledgeExchangeAdmin(admin.ModelAdmin):
#     list_display = ('file_name', 'action_type', 'status', 'timestamp')
#     list_filter = ('action_type', 'status')
#     readonly_fields = ('timestamp',)