from django.contrib import admin, messages
from django.db import transaction, models
from django.urls import path
from django.shortcuts import redirect, render
from django.utils.html import format_html
import json

from .models import (
    BusinessTerm, BusinessProcess, KnowledgeDraft, 
    BusinessLogicRule, AIPromptTemplate, SystemGuide
)

# --- 1. CẤU TRÚC INLINE (Sửa công thức ngay trong Bản thảo) ---

class BusinessLogicRuleInline(admin.TabularInline):
    """
    Nơi anh Vũ nắn gân AI: Sửa công thức 'bù tiền vàng cao tuổi' 
    ngay khi đang duyệt bản thảo từ Excel.
    """
    model = BusinessLogicRule
    extra = 1
    fields = ('rule_name', 'formula', 'variables', 'explanation')
    # Tăng kích thước ô nhập công thức cho dễ nhìn
    formfield_overrides = {
        models.TextField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 2, 'cols': 40})},
    }
    verbose_name = "Công thức/Logic bóc tách"
    verbose_name_plural = "Phần 4. Quy tắc Logic bóc tách (Đính kèm)"

# --- 2. QUẢN LÝ BẢN THẢO HỢP NHẤT (Trung tâm điều hành của anh Vũ) ---

@admin.register(KnowledgeDraft)
class KnowledgeDraftAdmin(admin.ModelAdmin):
    """
    WORKFLOW: Excel -> Miner -> Draft (Anh duyệt tại đây) -> Approved -> Chatbot Memory.
    """
    actions = ['approve_and_finalize_action']
    # Đã xóa 'sheet_name' để tránh lỗi "Cannot resolve keyword"
    list_display = ('title', 'category_label', 'project', 'colored_status', 'ai_execution_hub')
    list_filter = ('category', 'status', 'project')
    search_fields = ('title', 'content')
    
    inlines = [BusinessLogicRuleInline]

    # Style chuyên dụng cho dân kỹ thuật (Consolas font) để anh dễ soi JSON/Markdown
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 12, 
                'style': 'width: 100%; font-family: "Consolas", monospace; background: #fdf6e3; border: 1px solid #93a1a1;'
            })
        },
    }

    # --- UI Helpers (Icons cho loại dữ liệu tiệm vàng) ---
    def category_label(self, obj):
        icons = {'PROCESS': '⚙️ Quy trình', 'TERM': '📖 Thuật ngữ', 'LOGIC': '🧪 Logic'}
        return icons.get(obj.category, obj.category)
    category_label.short_description = "Loại dữ liệu"

    def colored_status(self, obj):
        colors = {'PENDING': '#E1AD01', 'AI_PROCESSED': '#2085EC', 'APPROVED': '#00AB66'}
        return format_html('<b style="color: {};">{}</b>', colors.get(obj.status, 'black'), obj.get_status_display())
    colored_status.short_description = "Trạng thái"

    def ai_execution_hub(self, obj):
        if obj.status == 'APPROVED':
            return format_html('<span style="color: #00AB66;">✅ Đã nạp tri thức</span>')
        
        btn_run = format_html(
            '<a class="button" style="background: #447e9b; margin-right: 5px;" href="./{}/run-ai/">🚀 AI Phân tích</a>', obj.pk
        )
        return format_html('{}', btn_run)
    ai_execution_hub.short_description = "Thao tác AI"

    # --- Logic AI Execution (Xử lý riêng lẻ từng bản ghi) ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/run-ai/', self.admin_site.admin_view(self.run_single_ai), name='knowledge-run-ai'),
        ]
        return custom_urls + urls

    def run_single_ai(self, request, object_id):
        # Import lazy để tránh lỗi import vòng lặp
        try:
            from apps.excel_miner.letter_AI import ExcelKnowledgeArchitect
            draft = self.get_object(request, object_id)
            
            # Chọn template phù hợp để AI không viết lạc đề
            t_name = "USER_GUIDE" if draft.category == 'PROCESS' else "TERM_GEN"
            
            architect = ExcelKnowledgeArchitect()
            success, message = architect.call_ai_with_dynamic_task(draft, template_name=t_name)
            
            if success:
                self.message_user(request, f"AI đã hoàn thành phân tích cho: {draft.title}")
            else:
                self.message_user(request, f"Lỗi AI: {message}", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"Lỗi hệ thống: {str(e)}", messages.ERROR)
            
        return redirect('admin:ai_knowledge_knowledgedraft_changelist')

# --- 3. QUẢN LÝ LOGIC (Ẩn bớt để tránh thừa, chỉ dùng khi cần soi kỹ) ---

@admin.register(BusinessLogicRule)
class BusinessLogicRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_name', 'variables_tags', 'short_formula', 'draft')
    list_filter = ('draft',)
    
    def variables_tags(self, obj):
        if not obj.variables: return "-"
        tags = "".join([f'<span style="background: #eee; padding: 2px 5px; margin: 2px; border-radius: 4px;">{v}</span>' for v in obj.variables])
        return format_html(tags)
    
    def short_formula(self, obj):
        return obj.formula[:50] + "..." if len(obj.formula) > 50 else obj.formula

# --- 4. CÁC MODEL CHÍNH THỨC (Dữ liệu đã "sạch") ---

@admin.register(BusinessTerm)
class BusinessTermAdmin(admin.ModelAdmin):
    list_display = ('term', 'is_common', 'created_at')
    search_fields = ('term',)

@admin.register(BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(AIPromptTemplate)
class AIPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'task_type')
    
    def get_urls(self):
        return [path('import-json/', self.admin_site.admin_view(self.import_json))] + super().get_urls()

    def import_json(self, request):
        # Giữ nguyên logic render template import JSON của anh Vũ
        return render(request, "admin/ai_import_promts_and_task_json.html")

@admin.register(SystemGuide)
class SystemGuideAdmin(admin.ModelAdmin):
    """Trang hướng dẫn tĩnh cho nhân viên tiệm vàng"""
    def has_add_permission(self, request): return False
    def changelist_view(self, request, extra_context=None):
        return render(request, "admin/system_manual.html", {'title': "📖 Hướng dẫn vận hành HTJ"})