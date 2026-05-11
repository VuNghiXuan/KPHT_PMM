from django.contrib import admin, messages
from django.db import models
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils import timezone
from django.utils.safestring import mark_safe
import json
from import_export.admin import ImportExportModelAdmin
# Import đúng các Model từ các app liên quan
from .services import KnowledgeService
from django.http import HttpResponse
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

# Import đúng các Model từ các app
from apps.app_miner.models import ExcelProject
from .models import LearningLog, KnowledgeDraft


@admin.register(KnowledgeDraft)
class KnowledgeDraftAdmin(admin.ModelAdmin):
    """
    TRUNG TÂM TINH CHẾ TRI THỨC (HTJ Knowledge Hub)
    Quy trình: Miner bóc quặng -> Đẩy vào Draft -> Nhấn nút '💡 AI Tinh chế' -> Anh Vũ sửa & Lưu.
    Mọi thao tác Save tại đây sẽ tự động đồng bộ ngược lại app_miner nhờ logic Model.
    """
    list_display = ('id', 'term', 'display_sheet', 'data_type', 'colored_status', 'ai_actions')
    list_filter = ('status', 'category', 'project', 'data_type')
    search_fields = ('term', 'content', 'sheet__name')
    
    readonly_fields = ('origin_metadata', 'backup_hash', 'updated_at', 'edit_datatype_link')
    # Cho phép tìm kiếm nhanh DataType thay vì scroll mỏi tay
    autocomplete_fields = ['data_type', 'project']

    # --- 1. Giao diện soạn thảo "Dark Mode" chuyên nghiệp ---
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 20, 
                'style': (
                    'width: 95%; font-family: "Fira Code", "Consolas", monospace; '
                    'background: #1e1e1e; color: #d4d4d4; line-height: 1.6; '
                    'padding: 15px; border-radius: 8px; border: 1px solid #333;'
                )
            })
        },
    }

    fieldsets = (
        ('📌 Định danh nghiệp vụ', {
            'fields': (
                ('term', 'category'), 
                ('project', 'data_type'), 
                'edit_datatype_link', 
                'status'
            )
        }),
        ('💡 Tri thức đã tinh chế (AI soạn / Anh Vũ sửa)', {
            'fields': ('content',),
            'description': mark_safe(
                "<b style='color:#ffa000;'>Lưu ý:</b> Nội dung này sẽ tự động đồng bộ sang "
                "mô tả của Excel Sheet sau khi anh nhấn Lưu."
            )
        }),
        ('🛠️ Metadata & Bảo mật (Dành cho Dev)', {
            'classes': ('collapse',), # Thu gọn lại cho đỡ rối
            'fields': ('origin_metadata', 'backup_hash', 'updated_at'),
        }),
    )

    # --- 2. UI Helpers: Hiển thị thông tin thông minh ---
    def display_sheet(self, obj):
        if obj.sheet:
            return obj.sheet.name
        return "-"
    display_sheet.short_description = "Sheet gốc"

    def edit_datatype_link(self, obj):
        """Link nhanh sang app_coach để sửa Prompt của AI"""
        if obj.data_type:
            url = reverse('admin:app_coach_datatype_change', args=[obj.data_type.pk])
            return mark_safe(
                f'<a href="{url}" target="_blank" style="color: #447e9b; font-weight: bold;">'
                f'⚙️ Tùy chỉnh Prompt cho: {obj.data_type.name}</a>'
            )
        return "Chưa gán DataType (Dùng Prompt mặc định)"
    edit_datatype_link.short_description = "Cấu hình AI"

    def colored_status(self, obj):
        colors = {
            'PENDING': '#7f8c8d',  # Xám
            'AI_READY': '#2980b9', # Xanh dương
            'EDITED': '#e67e22',   # Cam
            'FINAL': '#27ae60',    # Xanh lá
        }
        color = colors.get(obj.status, '#000')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-weight: bold; font-size: 10px;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = "Trạng thái"

    def ai_actions(self, obj):
        """Các nút bấm thao tác nhanh ngay tại danh sách"""
        refine_url = reverse('admin:ai-refine', args=[obj.pk])
        export_url = reverse('admin:knowledge-export', args=[obj.pk])
        return format_html(
            '<a class="button" style="background: #6f42c1; color:white; padding:4px 8px;" href="{}">💡 Tinh chế</a> '
            '<a class="button" style="background: #17a2b8; color:white; padding:4px 8px;" href="{}">📥 JSON</a>',
            refine_url, export_url
        )
    ai_actions.short_description = "Thao tác AI"

    # --- 3. Custom URLs & Logic Xử lý ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/refine/', self.admin_site.admin_view(self.run_ai_refine), name='ai-refine'),
            path('<int:object_id>/export/', self.admin_site.admin_view(self.export_single_json), name='knowledge-export'),
        ]
        return custom_urls + urls

    def run_ai_refine(self, request, object_id):
        """View kích hoạt AI xử lý cho 1 Draft lẻ"""
        success = KnowledgeService.refine_draft(object_id)
        if success:
            self.message_user(request, "AI đã hoàn thành việc tinh chế tri thức!", messages.SUCCESS)
        else:
            self.message_user(request, "AI gặp lỗi. Kiểm tra Metadata hoặc API Key.", messages.ERROR)
        return redirect('admin:app_knowledge_knowledgedraft_changelist')

    def export_single_json(self, request, object_id):
        """Xuất file Backup cho từng nghiệp vụ"""
        from django.http import HttpResponse
        obj = self.get_object(request, object_id)
        data = {
            'backup_hash': obj.backup_hash,
            'term': obj.term,
            'content': obj.content,
            'origin_metadata': obj.origin_metadata,
            'exported_at': str(timezone.now())
        }
        response = HttpResponse(
            json.dumps(data, indent=4, ensure_ascii=False), 
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="HTJ_Backup_{obj.backup_hash[:8]}.json"'
        return response

    # --- 4. Actions hàng loạt (Bulk Actions) ---
    actions = ['bulk_ai_refine']

    @admin.action(description="🤖 Chạy AI Tinh chế cho các dòng đã chọn")
    def bulk_ai_refine(self, request, queryset):
        total = queryset.count()
        count = 0
        
        # Duyệt qua danh sách các dòng anh đã tích chọn
        for i, draft in enumerate(queryset):
            # Gọi hàm xử lý đơn lẻ nhưng truyền index để hiện log tiến trình
            if KnowledgeService.refine_draft(draft.id, current_idx=i+1, total=total):
                count += 1
                
        self.message_user(
            request, 
            f"🚀 Hoàn thành: Đã tinh chế thành công {count}/{total} nghiệp vụ bằng AI.", 
            messages.SUCCESS
        )
        
# --- 1. ĐỊNH NGHĨA RESOURCE (Để hết lỗi Resolve) ---
class LearningLogResource(resources.ModelResource):
    project = fields.Field(
        column_name='project',
        attribute='project',
        widget=ForeignKeyWidget('app_miner.ExcelProject', 'name') # Dùng chuỗi ở đây luôn cho an toàn
    )

    class Meta:
        model = LearningLog
        fields = ('id', 'project', 'question', 'admin_answer', 'is_learned')
        import_id_fields = ['question'] 

# --- 2. GIAO DIỆN ADMIN ---
@admin.register(LearningLog)
class LearningLogAdmin(ImportExportModelAdmin):
    resource_class = LearningLogResource
    
    list_display = ('project', 'question_short', 'admin_answer', 'is_learned', 'updated_at')
    list_editable = ('admin_answer', 'is_learned')
    list_filter = ('is_learned', 'project')
    search_fields = ('question', 'admin_answer')
    ordering = ('-updated_at',)

    # Rút gọn câu hỏi hiển thị
    def question_short(self, obj):
        return obj.question[:70] + "..." if len(obj.question) > 70 else obj.question
    question_short.short_description = "Câu hỏi của AI"

    # Action xuất JSON
    actions = ['export_as_ai_knowledge']

    @admin.action(description="📤 Xuất file kiến thức cho AI (JSON)")
    def export_as_ai_knowledge(self, request, queryset):
        data = []
        for log in queryset:
            data.append({
                "q": log.question,
                "a": log.admin_answer or "Chưa trả lời",
                "learned": log.is_learned
            })
        
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=4),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="ai_knowledge_base.json"'
        return response

