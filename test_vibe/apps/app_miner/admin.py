import logging
from django.contrib import admin, messages
from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import reverse
from django.db import transaction
from django.utils.safestring import mark_safe

# Import các model mới theo cấu trúc Knowledge Hub
from .models import DataSource, DataEntry, ExcelTableRegion, DataField

logger = logging.getLogger(__name__)



@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    # Thêm 'system_map_view' vào danh sách hiển thị
    list_display = ('name', 'show_file_type', 'dashboard_view', 'system_map_view', 'stats_view', 'next_steps', 'show_status')
    list_filter = ('file_type', 'status')
    search_fields = ('name',)
    actions = ['re_run_miner', 'safe_clear_data']
    ordering = ('-uploaded_at',)

    # --- 1. Định dạng file có màu sắc ---
    def show_file_type(self, obj):
        colors = {
            'EXCEL': '#217346', # Xanh lá Excel
            'DOCX': '#2b579a',  # Xanh dương Word
            'TXT': '#666666',   # Xám nhạt
            'CSV': '#107c41',   # Xanh lục đậm
            'IMAGE': '#b93a3a'  # Đỏ ảnh (EasyOCR)
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.file_type, '#000'),
            obj.get_file_type_display()
        )
    show_file_type.short_description = "Định dạng"

    # --- 2. Dashboard tiến độ xử lý tri thức ---
    def dashboard_view(self, obj):
        entry_count = obj.entries.count()
        if entry_count == 0: 
            return mark_safe('<span style="color:gray;">Chờ bóc tách...</span>')

        completed_entries = obj.entries.filter(refine_status__in=['EXTRACTED', 'REFINED']).count()
        progress = (completed_entries / entry_count * 100) if entry_count > 0 else 0
        
        return mark_safe(f"""
            <div style="width:130px;">
                <div style="font-size:11px; margin-bottom:3px;">Tiến độ: <b>{completed_entries}/{entry_count} Mục</b></div>
                <div style="background:#eee; height:8px; border-radius:4px;">
                    <div style="background:#4caf50; width:{progress}%; height:100%; border-radius:4px;"></div>
                </div>
            </div>
        """)
    dashboard_view.short_description = "Tiến độ tri thức"

    # --- 3. HÀM MỚI BỔ SUNG: Sơ đồ phân phối hệ thống (System Map View) ---
    def system_map_view(self, obj):
        """
        Vẽ một mini-map trực quan hóa tỷ lệ phân loại dữ liệu bên trong nguồn này.
        Giúp sếp Vũ kiểm soát cấu trúc tri thức đầu vào.
        """
        if obj.file_type == 'EXCEL':
            # Đối với Excel: Đếm các loại ô chi tiết
            qs = DataField.objects.filter(sheet__project=obj)
            total = qs.count()
            if total == 0: return mark_safe('<span style="color:gray; font-size:11px;">Map trống</span>')
            
            logic_p = (qs.filter(field_type='LOGIC').count() / total) * 100
            data_p = (qs.filter(field_type='DATA').count() / total) * 100
            ui_trash_p = 100 - logic_p - data_p
            
            return mark_safe(f"""
                <div style="width: 140px; display: flex; height: 16px; border-radius: 3px; overflow: hidden; border: 1px solid #ccc;" title="⚙️ Logic: {logic_p:.1f}% | 📦 Data: {data_p:.1f}% | 🗑️ Rác/UI: {ui_trash_p:.1f}%">
                    <div style="background: #2196f3; width: {logic_p}%;"></div>
                    <div style="background: #4caf50; width: {data_p}%;"></div>
                    <div style="background: #e0e0e0; width: {ui_trash_p}%;"></div>
                </div>
            """)
        else:
            # Đối với các file Văn bản/Ảnh: Vẽ bản đồ tiến độ sẵn sàng nạp cho Chatbot Vector DB
            entries = obj.entries.all()
            total_entries = entries.count()
            if total_entries == 0: return mark_safe('<span style="color:gray; font-size:11px;">Chờ OCR...</span>')
            
            ready_count = entries.filter(refine_status='REFINED').count()
            extracted_count = entries.filter(refine_status='EXTRACTED').count()
            pending_count = total_entries - ready_count - extracted_count
            
            ready_p = (ready_count / total_entries) * 100
            extracted_p = (extracted_count / total_entries) * 100
            pending_p = (pending_count / total_entries) * 100
            
            return mark_safe(f"""
                <div style="width: 140px; display: flex; height: 16px; border-radius: 3px; overflow: hidden; border: 1px solid #ccc;" title="✅ Chuẩn RAG: {ready_p:.1f}% | 📄 Đang vét thô: {extracted_p:.1f}% | ⏳ Chờ xử lý: {pending_p:.1f}%">
                    <div style="background: #673ab7; width: {ready_p}%;"></div>
                    <div style="background: #009688; width: {extracted_p}%;"></div>
                    <div style="background: #ff9800; width: {pending_p}%;"></div>
                </div>
            """)
    system_map_view.short_description = "Bản đồ Tri thức (Map)"

    # --- 4. Sức khỏe dữ liệu (Tự động phân luồng hiển thị Excel vs File văn bản) ---
    def stats_view(self, obj):
        if obj.file_type == 'EXCEL':
            qs = DataField.objects.filter(sheet__project=obj)
            logic_count = qs.filter(field_type='LOGIC').count()
            ui_count = qs.filter(field_type='UI').count()
            data_count = qs.filter(field_type='DATA').count()
            
            return mark_safe(f"""
                <div style="line-height:1.2; font-size:11px;">
                    <span style="color:#2196f3;">⚙️ Logic: <b>{logic_count}</b></span><br>
                    <span style="color:#ff9800;">🖱️ UI/Nút: <b>{ui_count}</b></span><br>
                    <span style="color:#4caf50;">📦 Data: <b>{data_count:,}</b></span>
                </div>
            """)
        else:
            total_chars = sum([len(e.processed_content or '') for e in obj.entries.all()])
            return mark_safe(f"""
                <div style="line-height:1.2; font-size:11px; color: #673ab7;">
                    📝 Văn bản thô:<br><b>{total_chars:,} ký tự</b>
                </div>
            """)
    stats_view.short_description = "Dữ liệu thu hoạch"

    # --- 5. Phím tắt liên kết sang App Knowledge của Chatbot ---
    def next_steps(self, obj):
        try:
            draft_url = reverse('admin:app_knowledge_knowledgedraft_changelist') + f"?project__id__exact={obj.id}"
            log_url = reverse('admin:app_knowledge_learninglog_changelist') + f"?project__id__exact={obj.id}"
            
            from apps.app_knowledge.models import KnowledgeDraft
            total = KnowledgeDraft.objects.filter(project=obj).count()
            done = KnowledgeDraft.objects.filter(project=obj, status='AI_READY').count()
            bg_color = "#27ae60" if done == total and total > 0 else "#2c3e50"
            
            return mark_safe(f"""
                <div style="display:flex; gap:6px; align-items:center;">
                    <a class="button" style="background: {bg_color} !important; color: #fff !important; padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 10px; text-transform: uppercase; text-decoration: none;" href="{draft_url}">
                        📄 Tri thức: {done}/{total}
                    </a>
                    <a class="button" style="background: #e74c3c !important; color: #fff !important; padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 10px; text-transform: uppercase; text-decoration: none;" href="{log_url}">
                        ❓ AI Hỏi
                    </a>
                </div>
            """)
        except Exception:
            return mark_safe('<span style="color:gray; font-size:11px;">Chờ đồng bộ Chatbot</span>')
    next_steps.short_description = "Tinh chế nghiệp vụ"

    def show_status(self, obj):
        colors = {'PENDING': '#ffc107', 'PROCESSING': '#17a2b8', 'COMPLETED': '#28a745', 'FAILED': '#dc3545'}
        return format_html(
            '<strong style="color: {}; font-size: 12px;">{}</strong>',
            colors.get(obj.status, '#000'),
            obj.get_status_display()
        )
    show_status.short_description = "Trạng thái"

    @admin.action(description="🔄 Chạy lại Hệ thống bóc tách (Miner)")
    def re_run_miner(self, request, queryset):
        from .files_miner import DataMinerService
        for obj in queryset:
            try:
                DataMinerService.run_workflow(obj)
                self.message_user(request, f"Đã kích hoạt bóc tách nguồn tri thức: {obj.name}", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Lỗi xử lý nguồn {obj.name}: {str(e)}", messages.ERROR)

    @admin.action(description="🗑️ Xóa sạch dữ liệu gốc")
    def safe_clear_data(self, request, queryset):
        queryset.delete()
        self.message_user(request, "Đã dọn dẹp sạch sẽ kho dữ liệu thô.")

    # Chèn hàm này vào bên trong class DataSourceAdmin nha anh Vũ
    def save_model(self, request, obj, form, change):
        """
        Bắt sự kiện khi Sếp bấm 'Save' trên giao diện Admin.
        Nếu là file mới tạo (chưa có ID) hoặc file bị thay đổi path, tự động kích hoạt Miner.
        """
        # Kiểm tra xem file có bị thay đổi hoặc là file mới hoàn toàn không
        is_new_file = not obj.pk or 'file_path' in form.changed_data
        
        # 1. Vẫn cho Django lưu thông tin file vào Database trước
        super().save_model(request, obj, form, change)
        
        # 2. Nếu trúng điều kiện file mới, kích hoạt gọi luôn hàm xử lý ngầm
        if is_new_file:
            from .files_miner import ExcelMinerService # Thao tác import đúng tên file của anh
            try:
                # Kích hoạt chạy quy trình bóc tách tự động
                success, message = ExcelMinerService.run_workflow(obj)
                if success:
                    self.message_user(request, f"🚀 [Tự động] Đã kích hoạt khai thác thành công file: {obj.name}", messages.SUCCESS)
                else:
                    self.message_user(request, f"⚠️ [Tự động] Khai thác thất bại: {message}", messages.WARNING)
            except Exception as e:
                self.message_user(request, f"❌ Lỗi hệ thống khi chạy Miner: {str(e)}", messages.ERROR)
                
@admin.register(DataEntry)
class DataEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'category', 'status_badge', 'content_summary')
    list_filter = ('project__file_type', 'refine_status', 'category')
    search_fields = ('name', 'description', 'processed_content')
    readonly_fields = ('preview_content_rag',)
    
    fieldsets = (
        ("Thông tin chung", {'fields': ('project', 'name', 'category', 'description', 'refine_status')}),
        ("Dữ liệu bóc tách phục vụ Chatbot (RAG)", {'fields': ('preview_content_rag', 'content_json'), 'classes': ('collapse',)}),
        ("Cấu trúc Metadata cũ (Chỉ dùng cho Excel)", {'fields': ('metadata', 'confidence_score'), 'classes': ('collapse',)}),
    )

    def status_badge(self, obj):
        colors = {'PENDING': '#9e9e9e', 'EXTRACTED': '#2196f3', 'REFINED': '#4caf50'}
        return format_html('<span style="background:{}; color:white; padding:3px 10px; border-radius:10px; font-size:10px; font-weight:bold;">{}</span>', colors.get(obj.refine_status, '#000'), obj.get_refine_status_display())
    status_badge.short_description = "Trạng thái"

    def content_summary(self, obj):
        if obj.project.file_type == 'EXCEL':
            count = len(obj.metadata.get('logic_blocks', [])) if isinstance(obj.metadata, dict) else 0
            return format_html('<b style="color:#673ab7;">{} fx (Bảng tính)</b>', count)
        else:
            length = len(obj.processed_content or '')
            return format_html('<span style="color:#009688;">📄 {} ký tự thô</span>', f"{length:,}")
    content_summary.short_description = "Tóm tắt nội dung"

    def preview_content_rag(self, obj):
        if obj.processed_content:
            return format_html('<div style="background: #2c3e50; color: #fff; padding: 15px; border-radius: 6px; max-height: 400px; overflow-y: auto; font-family: monospace; white-space: pre-wrap; line-height:1.5;">{}</div>', obj.processed_content)
        return mark_safe('<em style="color:gray;">Không có nội dung text (Hoặc đây là file cấu trúc Excel)</em>')
    preview_content_rag.short_description = "Xem nhanh văn bản đích (Chatbot Feed)"


@admin.register(ExcelTableRegion)
class ExcelTableRegionAdmin(admin.ModelAdmin):
    list_display = ('sheet', 'name', 'region_type', 'coordinates_styled') 
    list_filter = ('sheet__project', 'region_type')
    search_fields = ('name', 'coordinates')

    def coordinates_styled(self, obj):
        return mark_safe(f'<code style="color: #e67e22; font-weight: bold; background: #fff3cd; padding: 2px 6px; border-radius: 3px;">{obj.coordinates}</code>')
    coordinates_styled.short_description = "Tọa độ Excel (Range)"


@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('cell_address', 'type_icon', 'label', 'display_value', 'sheet')
    list_filter = ('field_type', 'sheet__project', 'sheet')
    search_fields = ('cell_address', 'label', 'value', 'formula')

    def type_icon(self, obj):
        icons = {'LOGIC': '⚙️ Formula', 'UI': '🖱️ UI Component', 'DATA': '📦 Gold Data', 'TRASH': '🗑️ Empty'}
        colors = {'LOGIC': '#2196f3', 'UI': '#ff9800', 'DATA': '#4caf50', 'TRASH': '#9e9e9e'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colors.get(obj.field_type, '#000'), icons.get(obj.field_type, '❓'))
    type_icon.short_description = "Loại Ô"

    def display_value(self, obj):
        if obj.formula:
            return mark_safe(f'<code style="color:#d63384; font-size:11px; font-weight:bold;">{obj.formula[:60]}</code>')
        return (obj.value[:60] + '...') if obj.value and len(obj.value) > 60 else obj.value
    display_value.short_description = "Nội dung giá trị dữ liệu"