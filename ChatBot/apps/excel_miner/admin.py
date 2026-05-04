from django.contrib import admin, messages
from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import reverse
from django.db import transaction
from django.utils.safestring import mark_safe # Dùng cái này cho chắc ăn
import json

from .models import ExcelProject, ExcelSheet, DataField

@admin.register(ExcelProject)
class ExcelProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'uploaded_at', 'stats_view', 'next_steps')
    actions = ['preview_ai_payload', 'generate_blueprint_drafts', 'safe_clear_data']

    # --- HIỂN THỊ THỐNG KÊ ---
    def stats_view(self, obj):
        sheet_count = obj.sheets.count()
        field_count = DataField.objects.filter(sheet__project_id=obj.id).count()
        unlabeled = DataField.objects.filter(sheet__project_id=obj.id, label__isnull=True).exclude(value="").count()
        
        status_color = "#f44336" if unlabeled > 0 else "#4caf50"
        
        html = f"""
        <div style="line-height: 1.6;">
            📂 Sheets: <b>{sheet_count}</b><br>
            🔢 Cells: <b>{field_count:,}</b><br>
            ⚠️ Chờ duyệt: <span style="color:{status_color}; font-weight:bold;">{unlabeled:,}</span>
        </div>
        """
        return mark_safe(html)
    stats_view.short_description = "Sức khỏe dữ liệu"

    # --- ĐIỀU HƯỚNG NHANH ---
    def next_steps(self, obj):
        try:
            base_url = reverse('admin:ai_knowledge_knowledgedraft_changelist')
            p_url = f"{base_url}?project__id__exact={obj.id}&category__exact=PROCESS"
            t_url = f"{base_url}?project__id__exact={obj.id}&category__exact=TERM"
            
            html = (
                f'<a class="button" style="background:#447e9b;color:white;padding:2px 8px;display:inline-block;border-radius:4px;text-decoration:none;" href="{p_url}">📝 Quy trình</a> '
                f'<a class="button" style="background:#70bf2b;color:white;padding:2px 8px;display:inline-block;border-radius:4px;text-decoration:none;" href="{t_url}">🔍 Thuật ngữ</a>'
            )
            return mark_safe(html)
        except:
            return mark_safe('<span style="color: gray;">Chờ cấu hình...</span>')
    next_steps.short_description = "Hành động"

    # --- KÍCH HOẠT TỰ ĐỘNG HÓA KHI SAVE ---
    def save_model(self, request, obj, form, change):
        # 1. Lưu Project trước để FileField có path thực tế trên ổ cứng
        super().save_model(request, obj, form, change)
        
        # 2. Kiểm tra đúng tên trường là file_path (theo code excel_miner.py của anh)
        if obj.file_path and (not change or 'file_path' in form.changed_data):
            try:
                from .excel_miner import ExcelMinerService
                miner = ExcelMinerService()
                
                # Gọi hàm process_project
                success, message = miner.process_project(obj)
                
                if success:
                    self.message_user(request, f"Hệ thống KPHT đã bóc tách xong: {message}", messages.SUCCESS)
                else:
                    # Nếu có lỗi (ví dụ file sai định dạng), hiển thị traceback ra màn hình admin
                    self.message_user(request, f"Lỗi nghiệp vụ: {message}", messages.ERROR)
            except Exception as e:
                self.message_user(request, f"Lỗi hệ thống khi gọi Miner: {str(e)}", messages.ERROR)

    # --- CÁC ACTIONS GIỮ NGUYÊN ---
    @admin.action(description='🔍 Bước 0: Xem Blueprint (Dry Run)')
    def preview_ai_payload(self, request, queryset):
        from .letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        for project in queryset:
            blueprint = architect.generate_system_blueprint(project)
            print(f"--- DEBUG BLUEPRINT: {project.name} ---")
            print(json.dumps(blueprint, indent=2, ensure_ascii=False)[:1000] + "...")
        self.message_user(request, "Đã xuất Blueprint ra Console.", messages.INFO)

    @admin.action(description='📝 Bước 1: Soạn bản thảo (Drafting)')
    def generate_blueprint_drafts(self, request, queryset):
        from .letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        total_created = 0
        last_pid = None
        try:
            for project in queryset:
                count = architect.create_draft_processes_from_blueprint(project)
                total_created += count
                last_pid = project.id
            if total_created > 0:
                self.message_user(request, f"Đã tạo {total_created} bản thảo.", messages.SUCCESS)
                return redirect(reverse('admin:ai_knowledge_knowledgedraft_changelist') + f"?project__id__exact={last_pid}")
        except Exception as e:
            self.message_user(request, f"Lỗi: {str(e)}", messages.ERROR)

    @admin.action(description="🗑️ Xóa sạch dữ liệu")
    def safe_clear_data(self, request, queryset):
        from apps.ai_knowledge.models import KnowledgeDraft
        for project in queryset:
            with transaction.atomic():
                DataField.objects.filter(sheet__project=project).delete()
                KnowledgeDraft.objects.filter(project=project).delete()
                project.delete()
        self.message_user(request, "Đã dọn dẹp sạch sẽ.", messages.SUCCESS)

# --- QUẢN LÝ SHEETS ---
@admin.register(ExcelSheet)
class ExcelSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'sheet_index', 'category')
    list_filter = ('project', 'category')
    search_fields = ('name',)

# --- QUẢN LÝ DỮ LIỆU Ô (Nơi anh gắn nhãn nghiệp vụ) ---
@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('cell_address', 'get_sheet_name', 'display_value', 'label_status', 'is_verified')
    list_filter = ('sheet__project', 'is_verified', 'ui_type')
    list_editable = ('is_verified',)
    search_fields = ('value', 'label', 'cell_address')

    def get_sheet_name(self, obj):
        return obj.sheet.name
    get_sheet_name.short_description = "Sheet"

    def display_value(self, obj):
        val = str(obj.value or "")
        return val[:40] + "..." if len(val) > 40 else val
    display_value.short_description = "Giá trị gốc"

    def label_status(self, obj):
        if obj.label:
            return mark_safe(f'<span style="color: #2196f3;">🏷️ {obj.label}</span>')
        return mark_safe('<span style="color: #9e9e9e;">(Chưa gắn nhãn)</span>')
    label_status.short_description = "Định danh nghiệp vụ"