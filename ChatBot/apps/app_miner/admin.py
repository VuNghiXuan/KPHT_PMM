from django.contrib import admin, messages
from django.utils.html import format_html
from django.shortcuts import redirect, render
from django.urls import reverse, path
from django.db import transaction
from django.utils.safestring import mark_safe
import json
from .views import system_map_view

from .models import ExcelProject, ExcelSheet, ExcelTableRegion, DataField, UncertaintyLog

@admin.register(ExcelProject)
class ExcelProjectAdmin(admin.ModelAdmin):
    # --- 1. Dashboard tiến độ ---
    def dashboard_view(self, obj):
        total_fields = DataField.objects.filter(sheet__project=obj).count()
        if total_fields == 0: return "Chờ nạp dữ liệu..."

        logic_fields = DataField.objects.filter(sheet__project=obj).exclude(formula="").count()
        cross_sheet = DataField.objects.filter(sheet__project=obj, metadata__schema_mapping__is_cross_sheet=True).count()
        
        html = f"""
        <div class="kpht-dashboard">
            <div class="kpht-status-title"><b>Tiến độ dự án:</b> {obj.get_status_display()}</div>
            <div class="kpht-grid">
                <div class="kpht-card logic">
                    <small>Công thức (fx)</small><br><b>{logic_fields}</b>
                </div>
                <div class="kpht-card link">
                    <small>Liên kết Sheet</small><br><b>{cross_sheet}</b>
                </div>
            </div>
        </div>
        """
        return mark_safe(html)
    dashboard_view.short_description = "Bảng điều khiển"

    list_display = ('name', 'dashboard_view', 'stats_view', 'next_steps', 'status', 'view_guide_button')
    list_filter = ('status',)
    actions = ['preview_ai_payload', 'generate_blueprint_drafts', 'safe_clear_data']

    # --- 2. Thống kê sức khỏe dữ liệu ---
    def stats_view(self, obj):
        sheet_count = obj.sheets.count()
        field_count = DataField.objects.filter(sheet__project=obj).count()
        unlabeled = DataField.objects.filter(sheet__project=obj, label__isnull=True).exclude(value="").count()
        
        # Style màu trực tiếp cho biến số vẫn giữ lại một chút để linh hoạt
        color = "#f44336" if unlabeled > 0 else "#4caf50"
        
        return mark_safe(f"""
            <div class="kpht-stats">
                📁 Sheets: <b>{sheet_count}</b><br>
                🔢 Tổng ô: <b>{field_count:,}</b><br>
                ⚠️ Chưa nhãn: <b style="color:{color}">{unlabeled:,}</b>
            </div>
        """)
    stats_view.short_description = "Sức khỏe dữ liệu"

    # --- 3. Phím tắt nghiệp vụ ---
    def next_steps(self, obj):
        try:
            draft_url = reverse('admin:ai_knowledge_knowledgedraft_changelist') + f"?project__id__exact={obj.id}"
            log_url = reverse('admin:excel_miner_uncertaintylog_changelist') + f"?project__id__exact={obj.id}"
            
            # XÓA style="background:..." để CSS file có quyền kiểm soát
            return mark_safe(f"""
                <div class="kpht-btn-stack">
                    <a class="button btn-logic" href="{draft_url}">📊 Duyệt Logic</a>
                    <a class="button btn-ask" href="{log_url}">❓ AI Hỏi bài</a>
                </div>
            """)
        except: 
            return "-"
    next_steps.short_description = "Thao tác AI"

    list_display = ('name', 'dashboard_view', 'stats_view', 'next_steps', 'status', 'view_guide_button')
    
    # NẠP CSS VÀO ĐÂY
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

    # --- 4. Ghi đè hàm Save để kích hoạt Miner và đưa dữ liệu lên Neo4j---
    def save_model(self, request, obj, form, change):
        # 1. Lưu Project vào SQL trước
        super().save_model(request, obj, form, change)
        
        # 2. Đợi Database giải phóng khóa hoàn toàn rồi mới chạy Miner
        if obj.file_path:
            # Sử dụng on_commit để tránh lỗi "database is locked"
            transaction.on_commit(lambda: self._run_miner_logic(request, obj))

    def _run_miner_logic(self, request, obj):
        try:
            print(f"--- ĐANG KÍCH HOẠT MINER CHO: {obj.name} ---")
            from .excel_miner import ExcelMinerService
            
            miner = ExcelMinerService()
            success, message = miner.process_project(obj)
            
            if success:
                print(f"--- MINER XONG: {obj.name} ---")
            else:
                print(f"--- MINER CẢNH BÁO: {message} ---")
        except Exception as e:
            print(f"--- LỖI TẠI ADMIN: {str(e)} ---")

    @admin.action(description="🗑️ Xóa sạch dự án và tri thức liên quan")
    def safe_clear_data(self, request, queryset):
        for project in queryset:
            with transaction.atomic():
                DataField.objects.filter(sheet__project=project).delete()
                project.delete() # FileField sẽ tự xóa nhờ @receiver trong models.py
        self.message_user(request, "Đã dọn dẹp sạch sẽ dữ liệu.", messages.SUCCESS)

    def view_guide_button(self, obj):
        # Thêm !important vào color và background để đè CSS mặc định của Django Admin
        # Thêm display: inline-block để padding hoạt động chuẩn
        return format_html(
            '<a class="button" href="#" '
            'style="background-color: #607d8b !important; '
            'color: #ffffff !important; '
            'padding: 4px 10px; '
            'border-radius: 4px; '
            'text-decoration: none; '
            'font-weight: bold; '
            'display: inline-block; '
            'line-height: 1.5;">'
            '📖 Tài liệu</a>'
        )

    view_guide_button.short_description = "Hướng dẫn"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('system-map/', self.admin_site.admin_view(system_map_view), name='system_map'),
        ]
        return custom_urls + urls

    # Nút bấm để mở bản đồ (giữ nguyên logic reverse)
    def view_map_button(self, obj):
        # Dùng reverse để lấy đúng URL đã đăng ký trong get_urls
        # 'admin' là namespace, 'system_map' là cái name anh đặt trong path
        try:
            url = reverse('admin:system_map')
            return format_html('<a class="button" href="{}">🗺️ Bản đồ quy trình</a>', url)
        except Exception as e:
            return format_html('<span style="color:red">Lỗi link: {}</span>', str(e))

    view_map_button.short_description = "Quy trình"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # 'admin:system_map' phải khớp với 'name' trong get_urls của anh
        try:
            extra_context['guide_url'] = reverse('admin:system_map')
        except:
            extra_context['guide_url'] = "#"
        return super().changelist_view(request, extra_context=extra_context)
    
@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('cell_address', 'sheet_info', 'label_display', 'display_value', 'flow_indicator', 'is_required_badge')
    list_filter = ('sheet__project', 'sheet', 'is_required')
    search_fields = ('cell_address', 'label', 'value', 'formula')
    readonly_fields = ('metadata_json',)
    list_per_page = 50

    def sheet_info(self, obj):
        return f"{obj.sheet.name}"
    sheet_info.short_description = "Sheet"

    def label_display(self, obj):
        # Lấy nhãn thông minh từ metadata nếu label thủ công trống
        smart = obj.metadata.get('area_context', {}).get('smart_label', '')
        display = obj.label or smart
        if not display: return mark_safe('<span style="color:#ccc;">-</span>')
        icon = "🤖" if not obj.label else "🏷️"
        return mark_safe(f"<b>{icon} {display}</b>")
    label_display.short_description = "Nhãn nghiệp vụ"

    def display_value(self, obj):
        if obj.formula:
            return mark_safe(f'<code style="color: #d63384;">fx: {obj.formula[:40]}</code>')
        return obj.value[:30]
    display_value.short_description = "Giá trị/Công thức"

    def is_required_badge(self, obj):
        if obj.is_required:
            return mark_safe('<span style="color:red; font-weight:bold;">Bắt buộc</span>')
        return "Tùy chọn"
    is_required_badge.short_description = "Yêu cầu"

    def flow_indicator(self, obj):
        mapping = obj.metadata.get('schema_mapping', {})
        if mapping.get('is_cross_sheet'):
            return mark_safe('<span style="color:#01579b;">🔄 Liên kết sheet</span>')
        return "-"
    flow_indicator.short_description = "Luồng dữ liệu"

    def metadata_json(self, obj):
        # Dùng class CSS mới tách ra
        return mark_safe(f'<pre class="kpht-metadata-pre">{json.dumps(obj.metadata, indent=2, ensure_ascii=False)}</pre>')
    metadata_json.short_description = "Dữ liệu máy học"

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

@admin.register(UncertaintyLog)
class UncertaintyLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'question', 'is_learned')
    list_editable = ('is_learned',)
    list_filter = ('is_learned', 'project')

admin.site.register(ExcelSheet)
admin.site.register(ExcelTableRegion)