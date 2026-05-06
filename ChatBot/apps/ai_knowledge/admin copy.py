from django.contrib import admin, messages
from django.db import transaction, models
from django.urls import path
from django.shortcuts import redirect, render
from django.utils.html import format_html
import json

from .models import (
    BusinessTask, KnowledgeDraft, BusinessTerm, 
    BusinessProcess, CorrectionLedger
)

# --- 1. NHẬT KÝ SỬA LỖI (Dành cho học tăng cường) ---
class CorrectionLedgerInline(admin.TabularInline):
    model = CorrectionLedger
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('original_value', 'corrected_value', 'reason', 'created_at')
    verbose_name = "Nhật ký sửa lỗi (RLHF)"

# --- 2. QUẢN LÝ BẢN THẢO TRI THỨC (Trung tâm điều hành HTJ) ---

@admin.register(KnowledgeDraft)
class KnowledgeDraftAdmin(admin.ModelAdmin):
    """
    WORKFLOW: File -> Miner -> Router -> Draft (Duyệt tại đây) -> Approved -> Chatbot.
    """
    # Sửa list_display để không báo lỗi "Cannot resolve keyword"
    list_display = ('id', 'task_link', 'project_id', 'colored_status', 'created_at', 'ai_execution_hub')
    list_filter = ('task__task_type', 'status', 'task')
    search_fields = ('content', 'conflict_details')
    
    inlines = [CorrectionLedgerInline]

    # Style Consolas cho dân kỹ thuật để anh soi nội dung JSON/Markdown
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 12, 
                'style': 'width: 100%; font-family: "Consolas", monospace; background: #fdf6e3; border: 1px solid #93a1a1;'
            })
        },
    }

    # --- UI Helpers ---
    def task_link(self, obj):
        return format_html('<a href="/admin/ai_knowledge/businesstask/{}/change/">{}</a>', obj.task.pk, obj.task.name)
    task_link.short_description = "Nghiệp vụ liên kết"

    def colored_status(self, obj):
        colors = {'PENDING': '#E1AD01', 'CONFLICT': '#FF4136', 'APPROVED': '#00AB66'}
        return format_html('<b style="color: {};">{}</b>', colors.get(obj.status, 'black'), obj.get_status_display())
    colored_status.short_description = "Trạng thái đối soát"

    def ai_execution_hub(self, obj):
        if obj.status == 'APPROVED':
            return format_html('<span style="color: #00AB66;">✅ Đã thống nhất</span>')
        
        btn_run = format_html(
            '<a class="button" style="background: #447e9b;" href="./{}/run-ai/">🚀 AI Phân tích lại</a>', obj.pk
        )
        return btn_run
    ai_execution_hub.short_description = "Thao tác AI"

    # --- Logic AI Execution ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/run-ai/', self.admin_site.admin_view(self.run_single_ai), name='knowledge-run-ai'),
        ]
        return custom_urls + urls

    def run_single_ai(self, request, object_id):
        try:
            # Import lazy để tránh lỗi vòng lặp
            from apps.excel_miner.letter_AI import ExcelKnowledgeArchitect
            draft = self.get_object(request, object_id)
            
            architect = ExcelKnowledgeArchitect()
            # Dùng task_type từ BusinessTask để AI biết nhiệm vụ
            success, message = architect.call_ai_with_dynamic_task(draft, task_slug=draft.task.slug)
            
            if success:
                self.message_user(request, f"AI đã cập nhật nội dung cho bản thảo nghiệp vụ: {draft.task.name}")
            else:
                self.message_user(request, f"Lỗi AI: {message}", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"Lỗi hệ thống: {str(e)}", messages.ERROR)
            
        return redirect('admin:ai_knowledge_knowledgedraft_changelist')

# --- 3. QUẢN LÝ NGHIỆP VỤ ĐIỀU HƯỚNG ---

@admin.register(BusinessTask)
class BusinessTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'task_type', 'is_active', 'priority', 'import_export_btn')
    list_editable = ('is_active', 'priority')
    search_fields = ('name', 'slug')

    def import_export_btn(self, obj):
        return format_html('<a class="button" href="/admin/ai_knowledge/businesstask/import-json/">Import JSON</a>')
    import_export_btn.short_description = "Cấu hình"

    def get_urls(self):
        return [path('import-json/', self.admin_site.admin_view(self.import_json_view))] + super().get_urls()

    def import_json_view(self, request):
        return render(request, "admin/ai_import_prompts_and_task_json.html")

# --- 4. KHO TRI THỨC CHÍNH THỨC ---

@admin.register(BusinessTerm)
class BusinessTermAdmin(admin.ModelAdmin):
    list_display = ('term', 'is_active')
    search_fields = ('term', 'definition')

@admin.register(BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'task', 'is_published', 'updated_at')
    list_filter = ('is_published', 'task')
    list_editable = ('is_published',)

@admin.register(CorrectionLedger)
class CorrectionLedgerAdmin(admin.ModelAdmin):
    list_display = ('task', 'reason', 'created_at')
    readonly_fields = ('task', 'draft', 'original_value', 'corrected_value', 'reason', 'created_at')