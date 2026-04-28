from django.contrib import admin
from django.utils.html import format_html
from .models import ExcelProject, ExcelSheet, DataField

@admin.register(ExcelProject)
class ExcelProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'uploaded_at', 'file_link')
    ordering = ('-uploaded_at',) # Dự án mới nhất lên đầu
    
    def file_link(self, obj):
        if obj.file_path:
            return format_html('<a href="{}" target="_blank">📄 Xem File Gốc</a>', obj.file_path.url)
        return "Không có file"
    file_link.short_description = "Liên kết file"

@admin.register(ExcelSheet)
class ExcelSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'category', 'sheet_index')
    list_filter = ('project', 'category')
    search_fields = ('name',)

@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    # Thêm 'raw_value' vào list_display để anh đối chiếu với 'value'
    list_display = ('sheet', 'cell_address', 'display_value', 'get_raw_display', 'ai_summary', 'field_type', 'is_verified')
    
    list_filter = ('sheet__project', 'sheet__name', 'field_type', 'is_verified')
    search_fields = ('cell_address', 'value', 'comment', 'label')
    list_editable = ('is_verified',)
    
    # Cho xem chi tiết Metadata và mô tả nghiệp vụ trong trang edit
    readonly_fields = ('get_business_description', 'metadata_view', 'raw_value')

    def display_value(self, obj):
        """Hiển thị giá trị có màu sắc từ Excel"""
        color = obj.color_code if obj.color_code and obj.color_code not in ["N/A", "00000000"] else "f8f9fa"
        # Trả về mã màu để anh nhận diện Header/Button
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; background-color: #{}; color: #000; border: 1px solid #ddd; font-weight: bold;">{}</span>',
            color, obj.value[:30] if obj.value else "-"
        )
    display_value.short_description = "Giá trị hiển thị"

    def get_raw_display(self, obj):
        """Hiển thị giá trị gốc (Số/Ngày) để đối chiếu"""
        if obj.raw_value is not None:
            return format_html('<b style="color: #28a745;">{}</b>', obj.raw_value)
        return "-"
    get_raw_display.short_description = "Giá trị gốc (Raw)"

    def metadata_view(self, obj):
        """Hiển thị cục JSON Metadata đẹp đẽ"""
        import json
        return format_html(
            '<div style="background: #f4f4f4; padding: 10px; border-radius: 5px; border: 1px solid #ccc;">'
            '<pre style="margin: 0;">{}</pre></div>', 
            json.dumps(obj.metadata, indent=4, ensure_ascii=False)
        )
    metadata_view.short_description = "AI Context (Phân tích chuyên sâu)"