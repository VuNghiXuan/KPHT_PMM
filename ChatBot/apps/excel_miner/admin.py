from django.contrib import admin, messages
from django.utils.html import format_html
from django.shortcuts import redirect

from django.http import HttpResponse
import json

from .models import ExcelProject, ExcelSheet, DataField
from django.urls import reverse

@admin.register(ExcelProject)
class ExcelProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'uploaded_at', 'stats_view', 'next_steps')
    actions = [
        # 'fast_delete',                 # Xoá nhanh dữ liệu
        'preview_ai_payload',         # Bước 0: Xem thử Blueprint
        # 'collect_terms_to_draft',     # Bước 1: Nhặt từ thô vào nháp
        'generate_blueprint_drafts'   # Bước 2: Chuẩn bị bản thảo quy trình
    ]

    def next_steps(self, obj):
        """Tạo các nút bấm điều hướng nhanh theo luồng công việc"""
        # 1. Link tới trang soạn thảo quy trình (đã lọc theo project này)
        process_draft_url = reverse('admin:ai_knowledge_businessprocessdraft_changelist') + f"?project__id__exact={obj.id}"
        
        # 2. Link tới trang sàng lọc thuật ngữ
        term_draft_url = reverse('admin:ai_knowledge_businesstermdraft_changelist') + f"?project__id__exact={obj.id}"

        return format_html(
            '<a class="button" style="background: #447e9b; color: white; margin-right: 5px;" href="{}">📝 Soạn quy trình</a>'
            '<a class="button" style="background: #70bf2b; color: white;" href="{}">🔍 Duyệt thuật ngữ</a>',
            process_draft_url, term_draft_url
        )
    next_steps.short_description = "Luồng công việc"

    def stats_view(self, obj):
        """
        Hiển thị thống kê dữ liệu tối ưu hóa cho SQLite.
        Sử dụng đếm trực tiếp trên queryset của object để tránh lỗi 'too many SQL variables'.
        """
        # Đếm số lượng sheet trực tiếp từ relation
        sheet_count = obj.sheets.count()
        
        # Tối ưu: Truy vấn field thông qua relate_name (ví dụ: fields) của ExcelSheet 
        # Hoặc dùng trực tiếp filtering trên DataField như cũ nhưng đảm bảo dùng filter chính xác
        from .models import DataField
        
        # Đếm tổng số cell trong project
        field_count = DataField.objects.filter(sheet__project_id=obj.id).count()
        
        # Đếm số cell chưa có label và không rỗng
        # Lưu ý: Kiểm tra xem anh dùng 'label' hay 'smart_label' tùy theo bản cập nhật database mới nhất
        unlabeled = DataField.objects.filter(
            sheet__project_id=obj.id, 
            label__isnull=True
        ).exclude(value="").count()
        
        color = "red" if unlabeled > 0 else "green"
        
        return format_html(
            "<b>{}</b> Sheets | <b>{}</b> Cells | <span style='color:{}; font-weight:bold;'>{}</span> Chờ định nghĩa",
            sheet_count, field_count, color, unlabeled
        )
    stats_view.short_description = "Thống kê dữ liệu"

    @admin.action(description='🔍 0. Xem trước dữ liệu sẽ gửi AI (Dry Run)')
    def preview_ai_payload(self, request, queryset):
        # Local Import để né lỗi khởi động
        from .letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        
        for project in queryset:
            blueprint = architect.generate_system_blueprint(project)
            summary_msg = [f"=== BẢN TIN BLUEPRINT: {project.name} ==="]
            
            for sheet in blueprint.get("structure", []):
                sheet_name = sheet["sheet_name"]
                # Lọc đúng những gì AI sẽ thực sự đọc
                important = [
                    e for e in sheet["elements"] 
                    if e["group"] in ["ACTION_TRIGGER", "CRITICAL_INPUT_VALIDATION", "SECTION_HEADER"]
                ]
                
                count = len(important)
                sample = json.dumps(important[:2], ensure_ascii=False, indent=2)
                summary_msg.append(f"📍 Sheet: {sheet_name} | Gửi: {count} ô quan trọng.\nMẫu: {sample}\n")

            full_log = "\n".join(summary_msg)
            print(full_log) 
            self.message_user(request, f"Dự án '{project.name}': Đã trích xuất {len(blueprint['structure'])} sheets vào Console để anh check.", messages.SUCCESS)

    @admin.action(description='📥 1. Gom thuật ngữ thô vào Bản thảo')
    def collect_terms_to_draft(self, request, queryset):
        from .letter_AI import ExcelKnowledgeArchitect
        architect = ExcelKnowledgeArchitect()
        total_created = 0
        for project in queryset:
            count = architect.collect_terms_to_draft(project)
            total_created += count
        
        self.message_user(request, f"Đã nhặt {total_created} thuật ngữ thô. Anh qua mục 'Sàng lọc thuật ngữ (Draft)' để xem nhé.", messages.SUCCESS)

    @admin.action(description='📝 2. Chuẩn bị bản thảo quy trình (Chưa tốn Token)')
    def generate_blueprint_drafts(self, request, queryset):
        """
        Hành động Admin: Duyệt qua các Project được chọn, 
        tách từng Sheet thành một bản thảo (Draft) riêng biệt.
        """
        from django.shortcuts import redirect
        from django.urls import reverse
        from .letter_AI import ExcelKnowledgeArchitect
        
        architect = ExcelKnowledgeArchitect()
        total_sheets_created = 0
        last_project_id = None

        try:
            for project in queryset:
                # Gọi hàm Architect để bóc tách từng sheet
                # Hàm này giờ trả về số lượng sheet thành công
                count = architect.create_draft_processes_from_blueprint(project)
                total_sheets_created += count
                last_project_id = project.id
            
            if total_sheets_created > 0:
                self.message_user(
                    request, 
                    f"Thành công: Đã soạn xong bản thảo cho {total_sheets_created} Sheets từ {queryset.count()} dự án. "
                    "Hệ thống đang chuyển anh đến trang Soạn thảo quy trình...", 
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    "Không có bản thảo nào được tạo (có thể do các Sheet không chứa dữ liệu quan trọng).", 
                    messages.WARNING
                )

            # Tự động chuyển hướng đến danh sách bản thảo của Project cuối cùng được chọn
            if last_project_id:
                url = reverse('admin:ai_knowledge_businessprocessdraft_changelist') + f"?project__id__exact={last_project_id}"
                return redirect(url)

        except Exception as e:
            self.message_user(
                request, 
                f"Lỗi hệ thống khi tạo bản thảo: {str(e)}", 
                messages.ERROR
            )
    
    def delete_queryset(self, request, queryset):
        """Ghi đè để tránh lỗi 'too many SQL variables' khi xóa dự án lớn"""
        from .models import DataField, ExcelSheet
        
        for project in queryset:
            # 1. Xóa DataField trước theo từng sheet để giảm tải
            sheets = project.sheets.all()
            for sheet in sheets:
                DataField.objects.filter(sheet=sheet).delete()
            
            # 2. Xóa các bản nháp liên quan
            from apps.ai_knowledge.models import BusinessProcessDraft, BusinessTermDraft
            BusinessProcessDraft.objects.filter(project=project).delete()
            BusinessTermDraft.objects.filter(project=project).delete()
            
            # 3. Cuối cùng mới xóa Project (Sẽ kéo theo xóa Sheets vì Cascade)
            project.delete()
            
        self.message_user(request, "Đã xóa sạch dự án và các dữ liệu liên quan một cách an toàn.", messages.SUCCESS)

    @admin.action(description="🗑️ Xóa nhanh (Không tính toán)")
    def fast_delete(self, request, queryset):
        for obj in queryset:
            # Xóa trực tiếp thông qua DB (Bypass cơ chế thu thập thông tin của Admin)
            obj.delete()
        self.message_user(request, "Đã thực hiện xóa nhanh.")

# --- Các phần quản lý Sheet và Field giữ nguyên như anh đã viết ---

@admin.register(ExcelSheet)
class ExcelSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'sheet_index')
    list_filter = ('project',)
    ordering = ('project', 'sheet_index')

class FunctionalGroupFilter(admin.SimpleListFilter):
    title = 'Nhóm chức năng'
    parameter_name = 'func_group'
    def lookups(self, request, model_admin):
        return (
            ('ACTION_TRIGGER', 'Nút bấm / Lệnh'),
            ('SECTION_HEADER', 'Tiêu đề khối'),
            ('DATA_ENTRY', 'Ô nhập liệu'),
            ('CRITICAL_INPUT_VALIDATION', 'Ràng buộc quan trọng'),
        )
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(metadata__ui_context__functional_group=self.value())
        return queryset

@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('sheet', 'cell_address', 'display_value', 'is_verified', 'get_functional_group')
    list_filter = ('sheet__project', 'sheet__name', FunctionalGroupFilter)
    list_editable = ('is_verified',)
    readonly_fields = ('metadata_view',)
    search_fields = ('value', 'cell_address', 'label')

    def display_value(self, obj):
        if not obj.value: return "-"
        return obj.value[:50] + "..." if len(obj.value) > 50 else obj.value

    def get_functional_group(self, obj):
        try:
            group = obj.metadata.get('ui_context', {}).get('functional_group', '-')
            color_map = {
                'ACTION_TRIGGER': '#ff9800', # Cam
                'SECTION_HEADER': '#2196f3', # Xanh dương
                'CRITICAL_INPUT_VALIDATION': '#f44336' # Đỏ
            }
            color = color_map.get(group, '#4caf50') # Mặc định xanh lá
            return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, group)
        except:
            return "-"
    get_functional_group.short_description = "Phân loại AI"

    def metadata_view(self, obj):
        return format_html(
            '<pre style="background: #272822; color: #f8f8f2; padding: 10px; border-radius: 5px; font-size: 11px;">{}</pre>', 
            json.dumps(obj.metadata, indent=2, ensure_ascii=False)
        )
    metadata_view.short_description = "Cấu trúc Blueprint"