from django.contrib import admin, messages
# from django.http import HttpResponse
# from import_export import resources, fields
# from import_export.widgets import ForeignKeyWidget
# from import_export.admin import ImportExportModelAdmin
# import json

from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import reverse
from django.db import transaction
from django.utils.safestring import mark_safe

# Import các model
from .models import ExcelProject, ExcelSheet, ExcelTableRegion, DataField
# from apps.app_knowledge.models import KnowledgeDraft

@admin.register(ExcelProject)
class ExcelProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'dashboard_view', 'stats_view', 'next_steps', 'status')
    list_filter = ('status',)
    search_fields = ('name',)
    actions = ['re_run_miner', 'safe_clear_data']

    # --- 1. Dashboard tổng quan ---
    def dashboard_view(self, obj):
        sheet_count = obj.sheets.count()
        if sheet_count == 0: 
            return mark_safe('<span style="color:gray;">Chờ bóc tách...</span>')

        # Đếm số sheet đã được AI xử lý (REFINED)
        refined_sheets = obj.sheets.filter(refine_status='REFINED').count()
        progress = (refined_sheets / sheet_count * 100) if sheet_count > 0 else 0
        
        return mark_safe(f"""
            <div style="width:160px;">
                <div style="font-size:11px; margin-bottom:3px;">Tiến độ tinh chế: <b>{refined_sheets}/{sheet_count}</b></div>
                <div style="background:#eee; height:8px; border-radius:4px;">
                    <div style="background:#4caf50; width:{progress}%; height:100%; border-radius:4px;"></div>
                </div>
            </div>
        """)
    dashboard_view.short_description = "Tiến độ tri thức"

    # --- 2. Sức khỏe dữ liệu (Focus vào Logic và UI) ---
    def stats_view(self, obj):
        # Lấy stats từ các DataField thuộc project này
        qs = DataField.objects.filter(sheet__project=obj)
        logic_count = qs.filter(field_type='LOGIC').count()
        ui_count = qs.filter(field_type='UI').count()
        data_count = qs.filter(field_type='DATA').count()
        
        return mark_safe(f"""
            <div style="line-height:1.2; font-size:12px;">
                <span style="color:#2196f3;">⚙️ Logic: <b>{logic_count}</b></span><br>
                <span style="color:#ff9800;">🖱️ UI/Nút: <b>{ui_count}</b></span><br>
                <span style="color:#4caf50;">📦 Data: <b>{data_count:,}</b></span>
            </div>
        """)
    stats_view.short_description = "Sức khỏe hệ thống"

    # --- 3. Phím tắt thao tác nhanh ---
    def next_steps(self, obj):
        # 1. Link lọc danh sách (Giữ nguyên hoặc trỏ thẳng sang KnowledgeDraft cho tiện)
        draft_url = reverse('admin:app_knowledge_knowledgedraft_changelist') + f"?project__id__exact={obj.id}"
        log_url = reverse('admin:app_knowledge_learninglog_changelist') + f"?project__id__exact={obj.id}"
        
        # 2. Lấy số lượng thực tế từ Database
        # Anh nên import KnowledgeDraft ở đầu file để dùng chỗ này
        from apps.app_knowledge.models import KnowledgeDraft
        
        total = KnowledgeDraft.objects.filter(project=obj).count()
        done = KnowledgeDraft.objects.filter(project=obj, status='AI_READY').count()

        # 3. Đổi màu nút dựa trên tiến độ (Tùy chọn cho oai)
        bg_color = "#27ae60" if done == total and total > 0 else "#2c3e50"
        
        return mark_safe(f"""
            <div style="display:flex; gap:8px; align-items:center;">
                <a class="button" 
                    style="background: {bg_color} !important; color: #fff !important; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 11px; text-transform: uppercase; text-decoration: none;" 
                    href="{draft_url}">
                    📄 Tri thức: {done}/{total} Sheets
                </a>
                
                <a class="button" 
                    style="background: #e74c3c !important; color: #fff !important; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 11px; text-transform: uppercase; text-decoration: none;" 
                    href="{log_url}">
                    ❓ AI Hỏi bài
                </a>
            </div>
        """)
    next_steps.short_description = "Tinh chế nghiệp vụ" # Đổi tên cột cho sát nghĩa

    @admin.action(description="🔄 Chạy lại Miner (Quét & Gom Metadata)")
    def re_run_miner(self, request, queryset):
        from .excel_miner import ExcelMinerService
        for obj in queryset:
            success, msg = ExcelMinerService.run_workflow(obj)
            if success:
                self.message_user(request, f"Đã bóc tách xong {obj.name}", messages.SUCCESS)
            else:
                self.message_user(request, f"Lỗi tại {obj.name}: {msg[:100]}", messages.ERROR)

    @admin.action(description="🗑️ Xóa sạch dữ liệu")
    def safe_clear_data(self, request, queryset):
        queryset.delete()
        self.message_user(request, "Đã dọn dẹp sạch sẽ.")

@admin.register(ExcelSheet)
class ExcelSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'status_badge', 'category', 'confidence_display', 'logic_density')
    list_filter = ('project', 'refine_status', 'category')
    search_fields = ('name', 'description')
    
    def status_badge(self, obj):
        colors = {'PENDING': '#9e9e9e', 'EXTRACTED': '#2196f3', 'REFINED': '#4caf50'}
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{}</span>',
            colors.get(obj.refine_status, '#000'), obj.get_refine_status_display()
        )
    status_badge.short_description = "Trạng thái"

    def confidence_display(self, obj):
        score = obj.confidence_score * 100
        color = "green" if score >= 80 else "orange" if score >= 50 else "red"
        return mark_safe(f'<b style="color:{color};">{score:.1f}%</b>')
    confidence_display.short_description = "Độ tin cậy AI"

    def logic_density(self, obj):
        # Đếm nhanh số logic trong metadata gom
        count = len(obj.metadata.get('logic_blocks', []))
        return format_html('<b>{} fx</b>', count)
    logic_density.short_description = "Mật độ Logic"

@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('cell_address', 'type_icon', 'label', 'display_value', 'sheet')
    list_filter = ('field_type', 'sheet__project', 'sheet')
    search_fields = ('cell_address', 'label', 'value', 'formula')

    def type_icon(self, obj):
        icons = {'LOGIC': '⚙️', 'UI': '🖱️', 'DATA': '📦', 'TRASH': '🗑️'}
        return icons.get(obj.field_type, '❓')
    type_icon.short_description = "Loại"

    def display_value(self, obj):
        if obj.formula:
            return mark_safe(f'<code style="color:#d63384; font-size:11px;">{obj.formula[:50]}</code>')
        return (obj.value[:50] + '...') if obj.value and len(obj.value) > 50 else obj.value
    display_value.short_description = "Giá trị/Công thức"



# apps/app_miner/admin.py

@admin.register(ExcelTableRegion)
class ExcelTableRegionAdmin(admin.ModelAdmin):
    # Sử dụng các trường thực tế có trong Model: 'sheet', 'name', 'region_type', 'coordinates'
    list_display = ('sheet', 'name', 'region_type', 'coordinates_styled') 
    list_filter = ('sheet__project', 'region_type')
    search_fields = ('name', 'coordinates')

    # Hàm hiển thị tọa độ cho đẹp và nổi bật
    def coordinates_styled(self, obj):
        from django.utils.safestring import mark_safe
        # Trả về tọa độ kèm một chút màu sắc cho dễ phân biệt vùng
        return mark_safe(f'<code style="color: #e67e22; font-weight: bold;">{obj.coordinates}</code>')
    
    coordinates_styled.short_description = "Tọa độ (Range)"