from django.contrib import admin, messages
from django.db import models
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
import json

from .models import (
    BusinessTerm, BusinessProcess, IntentRouter, 
    BusinessTermDraft, BusinessProcessDraft, BusinessLogicRule
)

# --- 1. CẤU TRÚC INLINE ---

class BusinessTermDraftInline(admin.TabularInline):
    """Hiển thị danh sách thuật ngữ bóc tách được ngay trong trang quy trình."""
    model = BusinessTermDraft
    extra = 0
    fields = ('term', 'definition', 'ui_type', 'status')
    classes = ('collapse',) 
    verbose_name = "Thuật ngữ liên quan"
    verbose_name_plural = "Bóc tách thuật ngữ (Từ quy trình này)"

class BusinessLogicRuleInline(admin.TabularInline):
    """Hiển thị các công thức logic (vàng quy tuổi, bù khách...)"""
    model = BusinessLogicRule
    extra = 1
    # Thêm explanation để anh giải thích công thức bằng tiếng Việt bình dân
    fields = ('rule_name', 'formula', 'variables', 'explanation')
    verbose_name = "Công thức/Logic"
    verbose_name_plural = "Các logic tính toán (AI trích xuất)"

# --- 2. GIAO DIỆN CHÍNH (THE WORKSPACE) ---
@admin.register(BusinessProcessDraft)
class BusinessProcessDraftAdmin(admin.ModelAdmin):
    # CHỈ KHAI BÁO ACTIONS MỘT LẦN DUY NHẤT Ở ĐÂY
    actions = ['re_generate_by_ai', 'refine_selected_action', 'approve_and_finalize_action']

    # --- 1. Cấu hình hiển thị ---
    list_display = ('process_name', 'sheet_name', 'colored_status', 'run_ai_column', 'project')
    list_filter = ('status', 'project', 'sheet_name')
    search_fields = ('process_name', 'draft_content')
    inlines = [BusinessTermDraftInline, BusinessLogicRuleInline]

    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(
                attrs={
                    'rows': 15, 
                    'style': 'width: 100%; font-family: "Consolas", monospace; font-size: 14px; border: 2px solid #447e9b;'
                }
            )
        },
    }

    fieldsets = (
        ("Thông tin chung", {
            'fields': ('project', ('sheet_name', 'process_name'), 'status')
        }),
        ("Nội dung biên soạn AI (Markdown)", {
            'fields': ('draft_content',),
            'description': "Anh hãy gọt giũa quy trình tại đây. Sau đó nhấn 'Lưu' và dùng nút 'Tinh chỉnh' nếu cần AI làm mượt lại."
        }),
        ("Dữ liệu kỹ thuật", {
            'classes': ('collapse',),
            'fields': ('logic_mapping',),
        }),
    )

    # --- 2. Các hàm bổ trợ hiển thị ---
    def colored_status(self, obj):
        colors = {'PENDING': '#E1AD01', 'REVISED': '#2085EC', 'APPROVED': '#00AB66'}
        return format_html('<b style="color: {};">{}</b>', colors.get(obj.status, 'black'), obj.get_status_display())
    colored_status.short_description = "Trạng thái"

    def run_ai_column(self, obj):
        if obj.status == 'APPROVED':
            return format_html('<span style="color: gray;">✅ Đã duyệt</span>')
        
        # Nút 1: Chạy bóc tách từ Excel (Xanh biển)
        btn_run = format_html(
            '<a class="button" style="background: #447e9b; color: white; padding: 4px 8px; '
            'margin-right: 5px; display: inline-block; vertical-align: middle;" '
            'href="./{}/run-ai-single/">🚀 Chạy AI</a>', obj.pk
        )
        
        # Nút 2: Tinh chỉnh (Cam) - Chỉ hiện khi đã có nội dung
        btn_refine = ""
        if obj.draft_content:
            btn_refine = format_html(
                '<a class="button" style="background: #e1ad01; color: white; padding: 4px 8px; '
                'display: inline-block; vertical-align: middle;" '
                'href="./{}/refine-ai-single/">✨ Tinh chỉnh</a>', obj.pk
            )
        
        # Bọc tất cả vào một div để ép chúng nằm trên cùng 1 hàng
        return format_html(
            '<div style="white-space: nowrap; display: flex; align-items: center;">{}{}</div>', 
            btn_run, btn_refine
        )
    run_ai_column.short_description = "Thực thi"

    # --- 3. Xử lý URL tùy chỉnh ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/run-ai-single/', self.admin_site.admin_view(self.run_single_ai_logic)),
            path('<path:object_id>/refine-ai-single/', self.admin_site.admin_view(self.refine_single_ai_logic)),
        ]
        return custom_urls + urls

    # --- 4. Logic xử lý AI (Single) ---
    def run_single_ai_logic(self, request, object_id):
        from excel_miner.letter_AI import ExcelKnowledgeArchitect
        draft = self.get_object(request, object_id)
        if draft:
            architect = ExcelKnowledgeArchitect()
            success, message = architect.call_ai_to_write_process(draft) 
            if success: self.message_user(request, f"✅ {message}")
            else: self.message_user(request, f"❌ Lỗi: {message}", messages.ERROR)
        return redirect('..')

    def refine_single_ai_logic(self, request, object_id):
        from excel_miner.letter_AI import ExcelKnowledgeArchitect
        draft = self.get_object(request, object_id)
        if draft:
            if not draft.draft_content:
                self.message_user(request, "Chưa có nội dung để tinh chỉnh!", messages.WARNING)
                return redirect('..')
            architect = ExcelKnowledgeArchitect()
            success, message = architect.refine_ai_process(draft) 
            if success: self.message_user(request, f"✨ {message}")
            else: self.message_user(request, f"❌ Lỗi: {message}", messages.ERROR)
        return redirect('..')

    # --- 5. Actions (Xử lý hàng loạt) ---
    @admin.action(description="✨ 1b. AI biên tập lại nội dung đã sửa (Hàng loạt)")
    def refine_selected_action(self, request, queryset):
        from excel_miner.letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        success_count = 0
        for draft in queryset:
            # Kiểm tra nội dung có dữ liệu mới cho AI biên tập
            if draft.draft_content and draft.status != 'APPROVED':
                success, _ = architect.refine_ai_process(draft)
                if success:
                    success_count += 1
        self.message_user(request, f"Đã tinh chỉnh xong {success_count} bản thảo.", messages.SUCCESS)
    
    @admin.action(description="🚀 1a. AI viết lại quy trình từ Excel (Hàng loạt)")
    def re_generate_by_ai(self, request, queryset):
        from excel_miner.letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        success_count = 0
        for draft in queryset:
            # Chỉ chạy cho những bản chưa APPROVED để tránh ghi đè dữ liệu cũ
            if draft.status != 'APPROVED':
                success, _ = architect.call_ai_to_write_process(draft)
                if success:
                    success_count += 1
        self.message_user(request, f"Đã bóc tách xong {success_count} bản thảo từ Excel.", messages.SUCCESS)

    @admin.action(description="✅ 2. Phê duyệt & Đẩy vào bộ nhớ Chatbot")
    def approve_and_finalize_action(self, request, queryset):
        """
        Chuyển đổi Bản thảo thành tri thức chính thức cho hệ thống RAG của UDV.
        Sử dụng transaction.atomic() để đảm bảo an toàn dữ liệu.
        """
        from django.db import transaction
        from apps.ai_knowledge.models import BusinessProcess, BusinessTerm, BusinessLogicRule
        from django.contrib import messages

        success_count = 0
        try:
            with transaction.atomic():
                for draft in queryset:
                    # 1. Tạo hoặc cập nhật quy trình chính thức (BusinessProcess)
                    # Gom tất cả logic rules thành chuỗi văn bản để Chatbot dễ đọc
                    logic_summary = "\n".join([
                        f"- {r.rule_name}: {r.formula} ({r.variables})" 
                        for r in draft.logic_rules_draft.all()
                    ])
                    
                    process, created = BusinessProcess.objects.update_or_create(
                        project=draft.project,
                        name=draft.process_name,
                        defaults={
                            'description': draft.draft_content,
                            'logic_rules': logic_summary,
                            'sheet_reference': draft.sheet_name,
                        }
                    )
                    
                    # 2. Duyệt và đẩy các Thuật ngữ (BusinessTerm) sang bộ nhớ chính
                    # Liên kết qua related_terms (theo code Inline của anh)
                    term_drafts = draft.related_terms.all()
                    for t_draft in term_drafts:
                        BusinessTerm.objects.update_or_create(
                            project=draft.project,
                            term=t_draft.term,
                            defaults={
                                'definition': t_draft.definition,
                                'ui_type': t_draft.ui_type,
                                'context': f"Thuộc quy trình: {draft.process_name}"
                            }
                        )
                        # Đánh dấu bản thảo thuật ngữ đã xong
                        t_draft.status = 'DONE'
                        t_draft.save()

                    # 3. Cập nhật trạng thái bản thảo quy trình
                    draft.status = 'APPROVED'
                    draft.save()
                    success_count += 1
                
                self.message_user(
                    request, 
                    f"Đã chính thức hóa {success_count} quy trình và các thuật ngữ liên quan vào hệ thống UDV.", 
                    messages.SUCCESS
                )

        except Exception as e:
            self.message_user(
                request, 
                f"Lỗi hệ thống khi phê duyệt: {str(e)}", 
                messages.ERROR
            )

        
# --- 3. QUẢN LÝ THUẬT NGỮ & ROUTER ---

@admin.register(BusinessTermDraft)
class BusinessTermDraftAdmin(admin.ModelAdmin):
    list_display = ('term', 'sheet_name', 'definition', 'colored_status', 'project')
    list_editable = ('definition',) 
    list_filter = ('status', 'project', 'sheet_name')
    search_fields = ('term', 'definition')

    actions = ['approve_to_official_dict', 'delete_selected_trash']

    def colored_status(self, obj):
        colors = {'PENDING': '#E1AD01', 'SENT': '#2085EC', 'DONE': '#00AB66'}
        return format_html('<b style="color: {};">{}</b>', 
                           colors.get(obj.status, 'black'), obj.get_status_display())

    @admin.action(description="✅ Duyệt nạp (Chuyển sang Từ điển chính)")
    def approve_to_official_dict(self, request, queryset):
        success_count = 0
        for draft in queryset:
            if draft.definition:
                BusinessTerm.objects.update_or_create(
                    term=draft.term,
                    defaults={
                        'definition': draft.definition, 
                        'context': draft.context
                    }
                )
                draft.status = 'DONE'
                draft.save()
                success_count += 1
        self.message_user(request, f"Đã nạp chính thức {success_count} thuật ngữ.", messages.SUCCESS)

@admin.register(BusinessTerm)
class BusinessTermAdmin(admin.ModelAdmin):
    list_display = ('term', 'is_common', 'short_definition') 
    list_editable = ('is_common',)

    def short_definition(self, obj):
        return (obj.definition[:60] + "...") if obj.definition and len(obj.definition) > 60 else obj.definition

@admin.register(BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'has_logic_rules', 'created_at')
    readonly_fields = ('created_at',)

    def has_logic_rules(self, obj):
        return bool(obj.logic_rules)
    has_logic_rules.boolean = True

@admin.register(IntentRouter)
class IntentRouterAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'intent_name', 'target_app', 'hit_count_display')
    readonly_fields = ('hit_count',)

    def hit_count_display(self, obj):
        return format_html('<b style="color: #2196f3;">{} lượt hỏi</b>', obj.hit_count)