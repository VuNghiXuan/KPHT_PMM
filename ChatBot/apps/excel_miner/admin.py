from django.contrib import admin, messages
from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import path
from django.db import transaction
from django.utils.safestring import mark_safe # Dùng cái này cho chắc ăn
import json

from .models import ExcelProject, ExcelSheet, DataField
from .views import system_map_view



@admin.register(ExcelProject)
class ExcelProjectAdmin(admin.ModelAdmin):
    def dashboard_view(self, obj):
        # 1. Tính toán các chỉ số thực tế từ DB
        total_fields = DataField.objects.filter(sheet__project=obj).count()
        if total_fields == 0: return "Chờ nạp dữ liệu..."

        verified_fields = DataField.objects.filter(sheet__project=obj, is_verified=True).count()
        logic_fields = DataField.objects.filter(sheet__project=obj).exclude(formula="").count()
        cross_sheet = DataField.objects.filter(sheet__project=obj, metadata__schema_mapping__is_cross_sheet=True).count()
        
        # Tính tỷ lệ phần trăm hoàn thành
        percent_done = int((verified_fields / total_fields) * 100) if total_fields > 0 else 0
        
        # 2. Render HTML Dashboard mini
        html = f"""
        <div style="width: 300px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>Tiến độ xác thực:</span>
                <b>{percent_done}%</b>
            </div>
            <div style="width: 100%; background: #e9ecef; border-radius: 4px; height: 8px; margin-bottom: 10px;">
                <div style="width: {percent_done}%; background: #28a745; height: 100%; border-radius: 4px;"></div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
                <div style="background: white; padding: 5px; border-radius: 4px; border-left: 3px solid #ffc107;">
                    <small>Công thức (fx)</small><br><b>{logic_fields}</b>
                </div>
                <div style="background: white; padding: 5px; border-radius: 4px; border-left: 3px solid #17a2b8;">
                    <small>Liên kết sheet</small><br><b>{cross_sheet}</b>
                </div>
            </div>
        </div>
        """
        return mark_safe(html)
    dashboard_view.short_description = "Bảng điều khiển tiến độ"

    list_display = ('name', 'dashboard_view', 'uploaded_at', 'stats_view', 'next_steps', 'status',  'view_guide_button')
    actions = ['preview_ai_payload', 'generate_blueprint_drafts', 'safe_clear_data']

    # --- HIỂN THỊ THỐNG KÊ ---
    def stats_view(self, obj):
        sheet_count = obj.sheets.count()
        field_count = DataField.objects.filter(sheet__project_id=obj.id).count()
        unlabeled = DataField.objects.filter(sheet__project_id=obj.id, label__isnull=True).exclude(value="").count()
        
        status_color = "#f44336" if unlabeled > 0 else "#4caf50"
        cross_sheet_count = DataField.objects.filter(
            sheet__project_id=obj.id, 
            metadata__schema_mapping__is_cross_sheet=True
        ).count()
        
        html = f"""
        <div style="line-height: 1.6;">
            📂 Sheets: <b>{sheet_count}</b><br>
            🔢 Cells: <b>{field_count:,}</b><br>
            ⚠️ Chờ duyệt: <span style="color:{status_color}; font-weight:bold;">{unlabeled:,}</span>
            Liên kết: <b>{cross_sheet_count}</b>
        </div>
        """
        return mark_safe(html)
    stats_view.short_description = "Sức khỏe dữ liệu"

    # --- ĐIỀU HƯỚNG NHANH ---
    def next_steps(self, obj):
        try:
            base_url = reverse('admin:ai_knowledge_knowledgedraft_changelist')
            # Đổi PROCESS thành LOGIC để khớp với file Miner
            p_url = f"{base_url}?project__id__exact={obj.id}&category__exact=LOGIC"
            t_url = f"{base_url}?project__id__exact={obj.id}&category__exact=TERM"
            
            html = (
                f'<a class="button" style="background:#447e9b;color:white;padding:2px 8px;margin-right:5px;display:inline-block;border-radius:4px;text-decoration:none;" href="{p_url}">📊 Logic Vàng</a> '
                f'<a class="button" style="background:#70bf2b;color:white;padding:2px 8px;display:inline-block;border-radius:4px;text-decoration:none;" href="{t_url}">🔍 Thuật ngữ</a>'
            )
            return mark_safe(html)
        except:
            return mark_safe('<span style="color: gray;">Chờ cấu hình...</span>')

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

    # --- ACTION MỚI: XEM BỨC THƯ GỬI AI ---
    @admin.action(description='🔍 Bước 0: Xem Blueprint & Prompt (Gửi AI)')
    def preview_ai_payload(self, request, queryset):
        from .letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        
        for project in queryset:
            # Lấy prompt từ DB cho nhiệm vụ viết code
            ai_package = architect.create_prompt_for_ai(project, task_type='GEN_CODE')
            
            if ai_package:
                print(f"\n=== SYSTEM PROMPT FOR {project.name} ===\n")
                print(ai_package['system'])
                print(f"\n=== USER PROMPT (DATA CONTEXT) ===\n")
                print(ai_package['user'][:2000] + "...") # Xem trước 2000 ký tự
                self.message_user(request, f"Đã xuất 'Bức thư gửi AI' cho {project.name} ra Console.", messages.INFO)
            else:
                self.message_user(request, f"Vui lòng cấu hình Prompt Template cho 'GEN_CODE' trong DB trước.", messages.WARNING)

    @admin.action(description='📝 Bước 1: Soạn bản thảo (Drafting Logic Flows)')
    def generate_blueprint_drafts(self, request, queryset):
        from .letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        total_created = 0
        for project in queryset:
            # Gọi hàm mới đã tối ưu
            count = architect.create_logic_drafts_from_formulas(project)
            total_created += count
            
        if total_created > 0:
            self.message_user(request, f"Đã nhận diện {total_created} bản thảo logic.", messages.SUCCESS)
            # Điều hướng thẳng đến danh sách bản thảo để anh duyệt luôn
            return redirect(reverse('admin:ai_knowledge_knowledgedraft_changelist') + f"?project__id__exact={queryset[0].id}")
        

    @admin.action(description="🗑️ Xóa sạch dữ liệu")
    def safe_clear_data(self, request, queryset):
        from apps.ai_knowledge.models import KnowledgeDraft
        for project in queryset:
            with transaction.atomic():
                DataField.objects.filter(sheet__project=project).delete()
                KnowledgeDraft.objects.filter(project=project).delete()
                project.delete()
        self.message_user(request, "Đã dọn dẹp sạch sẽ.", messages.SUCCESS)
    
    # --- HIỂN THỊ HƯỚNG DẪN TRÌNH TỰ---
    # 1. Đăng ký URL riêng cho trang hướng dẫn bên trong Admin này
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # SỬA Ở ĐÂY: self.admin_view -> self.admin_site.admin_view
            path(
                'guide/', 
                self.admin_site.admin_view(system_map_view), 
                name='excel_project_guide'
            ),
        ]
        return custom_urls + urls

    # 2. Tạo nút bấm hiển thị ở mỗi dòng hoặc trên thanh công cụ
    def view_guide_button(self, obj):
        # Giữ nguyên phần này
        url = reverse('admin:excel_project_guide')
        return format_html(
            '<a class="button" href="{}" style="background-color: #E1AD01; color: white;">📖 Hướng dẫn</a>',
            url
        )    
    view_guide_button.short_description = "Hướng dẫn"

    # 3. Thêm nút "Xem hướng dẫn" to đùng ở phía trên bảng (Chỗ gần nút Thêm)
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['guide_url'] = reverse('admin:excel_project_guide')
        return super().changelist_view(request, extra_context=extra_context)

# --- QUẢN LÝ SHEETS ---
@admin.register(ExcelSheet)
class ExcelSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'sheet_index', 'category')
    list_filter = ('project', 'category')
    search_fields = ('name',)

# --- QUẢN LÝ DỮ LIỆU Ô (Nơi anh gắn nhãn nghiệp vụ) ---
@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    # Cấu hình các cột hiển thị chính
    list_display = (
        'cell_address', 
        'get_sheet_name', 
        'label_display',        # Hiển thị kết hợp label và smart_label
        'display_value', 
        'flow_indicator',       # Chỉ báo luồng dữ liệu (Schema Mapping)
        'ui_type',
        'ui_type_badge',        # Badge màu sắc cho loại thành phần
        'is_verified'
    )
    
    # Bộ lọc thông minh
    list_filter = (
        ('sheet', admin.RelatedOnlyFieldListFilter), # Lọc chỉ những sheet của project đang chọn
        'ui_type', 
        'is_verified',
    )
    # Thêm autocomplete cho label nếu anh có danh mục label riêng
    autocomplete_fields = ['sheet']
    
    # Cho phép sửa nhanh trạng thái xác minh và loại thành phần ngay tại danh sách
    list_editable = ('is_verified', 'ui_type')
    
    # Tìm kiếm đa trường
    search_fields = ('value', 'label', 'smart_label', 'cell_address', 'formula')
    
    # Tối ưu hiệu năng truy vấn
    list_select_related = ('sheet', 'sheet__project', 'field_type')
    list_per_page = 50

    # --- CÁC HÀM HIỂN THỊ CỘT CUSTOM ---

    def get_sheet_name(self, obj):
        return obj.sheet.name
    get_sheet_name.short_description = "Sheet"

    def label_display(self, obj):
        """Ưu tiên hiển thị Smart Label từ AI, sau đó đến Label thủ công."""
        main_label = obj.smart_label or obj.label
        if main_label:
            color = "#2196f3" if obj.smart_label else "#4caf50"
            icon = "🤖" if obj.smart_label else "🏷️"
            return mark_safe(f'<span style="color: {color}; font-weight: bold;">{icon} {main_label}</span>')
        return mark_safe('<span style="color: #9e9e9e;">(Chưa định danh)</span>')
    label_display.short_description = "Định danh nghiệp vụ"

    def display_value(self, obj):
        """Hiển thị giá trị hoặc công thức Excel với định dạng Code."""
        if obj.formula:
            return mark_safe(
                f'<code style="color: #d63384; background: #fff5f8; padding: 2px 4px; '
                f'border-radius: 4px; border: 1px solid #f1dae2;" title="{obj.formula}">'
                f'fx: {obj.formula[:30]}...</code>'
            )
        val = str(obj.value or "")
        return val[:40] + "..." if len(val) > 40 else val
    display_value.short_description = "Giá trị / Công thức"

    def ui_type_badge(self, obj):
        """Tạo badge màu sắc cho từng loại thành phần giao diện."""
        colors = {
            'INPUT': '#4caf50',   # Xanh lá: Nhập liệu
            'OUTPUT': '#f44336',  # Đỏ: Kết quả
            'HEADER': '#ff9800',  # Cam: Tiêu đề
            'BUTTON': '#9c27b0',  # Tím: Nút bấm
        }
        color = colors.get(obj.ui_type, '#757575')
        return mark_safe(
            f'<span style="background: {color}; color: white; padding: 3px 8px; '
            f'border-radius: 4px; font-size: 11px; font-weight: bold;">'
            f'{obj.get_ui_type_display()}</span>'
        )
    ui_type_badge.short_description = "Loại UI"

    def flow_indicator(self, obj):
        """Nhận diện luồng dữ liệu xuyên sheet từ Metadata."""
        mapping = obj.metadata.get('schema_mapping', {})
        depends = mapping.get('depends_on_sheets', [])
        
        if mapping.get('is_cross_sheet') and depends:
            sheets_str = ", ".join(depends)
            return mark_safe(
                f'<span style="background: #e1f5fe; color: #01579b; padding: 3px 10px; '
                f'border-radius: 12px; font-size: 11px; border: 1px solid #b3e5fc;" '
                f'title="Lấy dữ liệu từ: {sheets_str}">🔄 {len(depends)} Sheets</span>'
            )
        
        if obj.formula:
            return mark_safe('<span style="color: #8bc34a;" title="Tính toán trong sheet">📊 Nội bộ</span>')
            
        return mark_safe('<span style="color: #eceff1;">-</span>')
    flow_indicator.short_description = "Luồng dữ liệu"

    # --- TRANG CHI TIẾT (FORM VIEW) ---

    readonly_fields = ('metadata_json', 'confidence_display')

    def confidence_display(self, obj):
        """Hiển thị độ tin cậy của AI dưới dạng phần trăm."""
        score = obj.confidence_score * 100
        color = "#4caf50" if score > 80 else "#ff9800"
        return mark_safe(f'<b style="color: {color}; font-size: 1.2em;">{score:.1f}%</b>')
    confidence_display.short_description = "Độ tin cậy AI"

    def metadata_json(self, obj):
        """Render JSON Metadata đẹp mắt để kiểm tra kỹ thuật."""
        result = json.dumps(obj.metadata, indent=4, ensure_ascii=False)
        return mark_safe(
            f'<pre style="background: #1e1e1e; color: #dcdcdc; padding: 15px; '
            f'border-radius: 8px; font-family: Consolas, monospace; overflow: auto;">{result}</pre>'
        )
    metadata_json.short_description = "Chi tiết kỹ thuật (JSON)"

    fieldsets = (
        ('📍 Tọa độ & Xác thực', {
            'fields': (('sheet', 'cell_address'), ('is_verified', 'confidence_display'))
        }),
        ('🏷️ Định danh nghiệp vụ', {
            'fields': (('label', 'smart_label'), 'functional_group')
        }),
        ('📝 Nội dung & Logic', {
            'fields': ('value', 'formula', 'logic_interpretation', 'raw_value')
        }),
        ('🎨 Giao diện & Kỹ thuật', {
            'fields': (('ui_type', 'field_type'), ('color_code', 'is_required'))
        }),
        ('🤖 Dữ liệu máy học (Metadata)', {
            'classes': ('collapse',),
            'fields': ('metadata_json',),
        }),
    )

# Nâng cấp bộ lọc "Thông minh" cho Dashboard
class GoldLogicFilter(admin.SimpleListFilter):
    title = 'Trọng tâm nghiệp vụ'
    parameter_name = 'gold_logic'

    def lookups(self, request, model_admin):
        return (
            ('cross_sheet', '🔄 Liên kết xuyên Sheet'),
            ('high_val', '💰 Giá trị cao (Vàng/Tiền)'),
            ('unverified_logic', '⚠️ Logic chưa duyệt'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'cross_sheet':
            return queryset.filter(metadata__schema_mapping__is_cross_sheet=True)
        if self.value() == 'unverified_logic':
            return queryset.exclude(formula="").filter(is_verified=False)
        return queryset