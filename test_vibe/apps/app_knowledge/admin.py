from django.contrib import admin, messages
from django.db import models
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils import timezone
from django.utils.safestring import mark_safe
import json
import logging

from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .services import KnowledgeService
from .models import LearningLog, KnowledgeDraft
from .views import agent_workflow_map

logger = logging.getLogger(__name__)

@admin.register(KnowledgeDraft)
class KnowledgeDraftAdmin(admin.ModelAdmin):
    """
    HTJ Knowledge Hub - Nơi anh Vũ kiểm soát và phê duyệt tri thức hệ thống từ AI Miner
    """
    list_display = ('id', 'term', 'display_sheet', 'data_type', 'colored_status', 'ai_actions', 'view_map_button')
    list_filter = ('status', 'category', 'project', 'data_type')
    search_fields = ('term', 'content', 'sheet__name')
    autocomplete_fields = ['data_type', 'project']

    # --- 1. Giao diện soạn thảo Chuyên nghiệp ---
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 20, 
                'style': (
                    'width: 95%; font-family: "Fira Code", "Courier New", monospace; '
                    'background: #1e1e1e; color: #d4d4d4; line-height: 1.6; '
                    'font-size: 14px; '
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
            'description': mark_safe("<b style='color:#ffa000;'>Lưu ý:</b> Khi chuyển trạng thái sang EDITED hoặc FINAL và bấm Lưu, hệ thống sẽ tự động đồng bộ tri thức về Sheet gốc.")
        }),
        ('🛠️ Metadata & Bảo mật', {
            'classes': ('collapse',),
            'fields': ('origin_metadata_v2', 'backup_hash', 'updated_at'),
        }),
    )

    readonly_fields = ('origin_metadata_v2', 'backup_hash', 'updated_at', 'edit_datatype_link')

    # --- 2. UI Helpers ---
    def display_sheet(self, obj):
        return obj.sheet.name if obj.sheet else "-"
    display_sheet.short_description = "Sheet gốc"

    def edit_datatype_link(self, obj):
        """Link nhanh sang cấu hình Prompt mà không gây lỗi Circular Import"""
        if obj.data_type:
            from django.apps import apps
            try:
                AIPromptConfig = apps.get_model('app_ai_core', 'AIPromptConfig')
                config = AIPromptConfig.objects.filter(
                    module_code=obj.data_type.code, 
                    is_active=True
                ).first()

                if config:
                    url = reverse('admin:app_ai_core_aipromptconfig_change', args=[config.pk])
                    return mark_safe(
                        f'<a href="{url}" target="_blank" style="color: #ffa000; font-weight: bold;">'
                        f'⚙️ Sửa Prompt cho {obj.data_type.name}</a>'
                    )
            except (LookupError, Exception):
                pass
                
        return "Đang dùng cấu hình AI mặc định"

    edit_datatype_link.short_description = "Cấu hình AI"

    def colored_status(self, obj):
        colors = {'PENDING': '#7f8c8d', 'AI_READY': '#2980b9', 'EDITED': '#e67e22', 'FINAL': '#27ae60', 'ERROR': '#c0392b'}
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000'), obj.get_status_display()
        )
    colored_status.short_description = "Trạng thái"

    def ai_actions(self, obj):
        refine_url = reverse('admin:ai-refine', args=[obj.pk])
        export_url = reverse('admin:knowledge-export', args=[obj.pk])
        return format_html(
            '<a class="button" style="background: #e67e22; color:white; padding:4px 10px; border-radius:15px; text-decoration:none; margin-right:5px;" href="{}">💡 Tinh chế</a>'
            '<a class="button" style="background: #27ae60; color:white; padding:4px 10px; border-radius:15px; text-decoration:none;" href="{}">📥 JSON</a>',
            refine_url, export_url
        )
    ai_actions.short_description = "Thao tác"

    def origin_metadata_v2(self, obj):
        if not obj.origin_metadata: return "N/A"
        try:
            rows = "".join([f"<tr><td style='border:1px solid #444; padding:4px;'><b>{k}</b></td><td style='border:1px solid #444; padding:4px;'>{v}</td></tr>" for k, v in obj.origin_metadata.items()])
            return mark_safe(f"<table style='width:100%; border-collapse: collapse; background:#252526; font-size:12px;'>{rows}</table>")
        except: return str(obj.origin_metadata)
    origin_metadata_v2.short_description = "Metadata gốc"

    # --- 3. Logic Xử lý & Đồng bộ ---
    def save_model(self, request, obj, form, change):
        """
        Đồng bộ tri thức an toàn sang app_miner khi Anh Vũ phê duyệt
        """
        super().save_model(request, obj, form, change)
        
        # 🛡️ VÁ LỖI BẢO VỆ: Chỉ đồng bộ khi nội dung thực sự có chữ, tránh đè rỗng làm mất data Excel
        if obj.status in ['EDITED', 'FINAL'] and obj.sheet and obj.content and obj.content.strip():
            obj.sheet.description = obj.content
            obj.sheet.save(update_fields=['description'])
            self.message_user(request, f"🔄 Đã đồng bộ tri thức vào Sheet: {obj.sheet.name}", messages.SUCCESS)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/refine/', self.admin_site.admin_view(self.run_ai_refine), name='ai-refine'),
            path('<int:object_id>/export/', self.admin_site.admin_view(self.export_single_json), name='knowledge-export'),
            path('<int:project_id>/map/', self.admin_site.admin_view(agent_workflow_map), name='project-map'),
        ]
        return custom_urls + urls

    def view_map_button(self, obj):
        if obj.project:
            url = reverse('admin:project-map', args=[obj.project.id])
            return format_html('<a class="button" href="{}">🗺️ Xem sơ đồ</a>', url)
        return "N/A"
    view_map_button.short_description = "Bản đồ"
    
    def run_ai_refine(self, request, object_id):
        # 🏎️ TỐI ƯU RAM: Lấy thẳng instance object có sẵn thay vì truyền ID thô sang Service truy vấn lại
        draft_obj = self.get_object(request, object_id)
        
        if not draft_obj:
            self.message_user(request, "❌ Không tìm thấy dữ liệu nghiệp vụ này.", messages.ERROR)
            return redirect(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist')

        try:
            success = KnowledgeService.refine_draft(draft_obj)
            if success:
                self.message_user(request, "🎉 AI đã hoàn thành tinh chế & phân bổ nhóm nghiệp vụ!", messages.SUCCESS)
            else:
                self.message_user(request, "❌ AI lỗi. Kiểm tra cấu hình Prompt hoặc Log hệ thống.", messages.ERROR)
        except Exception as e:
            if "STOP_BATCH" in str(e):
                self.message_user(request, "🛑 Hết hạn mức API Cloud Free hôm nay! Vui lòng quay lại vào ngày mai.", messages.ERROR)
            else:
                self.message_user(request, f"💥 Lỗi hệ thống: {str(e)}", messages.ERROR)
        
        opts = self.model._meta
        return redirect(f'admin:{opts.app_label}_{opts.model_name}_changelist')

    def export_single_json(self, request, object_id):
        obj = self.get_object(request, object_id)
        data = {'term': obj.term, 'content': obj.content, 'metadata': obj.origin_metadata, 'date': str(timezone.now())}
        response = HttpResponse(json.dumps(data, indent=4, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="HTJ_{obj.id}.json"'
        return response

    actions = ['refine_selected_project_batch']

    @admin.action(description="🚀 CÀN QUÉT AI: Chỉ chạy các Sheet được tích chọn")
    def refine_selected_project_batch(self, request, queryset):
        """
        Hành động Batch Action: Chạy tối ưu hóa RAM, tự động ngắt nếu dính STOP_BATCH.
        """
        # Sử dụng select_related để gom toàn bộ dữ liệu vào RAM theo queryset anh Vũ chọn trên UI
        queryset = queryset.select_related('sheet', 'project', 'data_type')
        total_selected = queryset.count()
        
        if total_selected == 0:
            self.message_user(request, "Vui lòng chọn ít nhất một nghiệp vụ để chạy.", messages.WARNING)
            return

        success_count = 0
        shared_context = None
        stop_by_quota = False
        
        first_item = queryset.first()
        if first_item and first_item.project:
            shared_context = KnowledgeService._get_learned_context(first_item.project.id)

        # Duyệt qua từng object đã được cache sẵn trong RAM từ queryset
        for draft_obj in queryset:
            try:
                status = KnowledgeService.refine_draft(draft_obj, external_context=shared_context)
                if status:
                    success_count += 1
            except Exception as batch_err:
                # 🛑 NGẮT VÒNG LẶP UI: Nếu Gateway báo STOP_BATCH, dừng bấm máy ngay lập tức
                if "STOP_BATCH" in str(batch_err):
                    stop_by_quota = True
                    break
                logger.error(f"Lỗi hàng loạt tại Admin Action với ID {draft_obj.id}: {str(batch_err)}")

        if stop_by_quota:
            self.message_user(
                request, 
                f"🛑 Tiến trình tạm dừng nửa chừng do HẾT HẠN MỨC API FREE. Đã kịp xử lý thành công {success_count}/{total_selected} sheet. Số còn lại vẫn giữ nguyên trạng thái.", 
                messages.ERROR
            )
        else:
            self.message_user(
                request, 
                f"⚡ Khai thác thành công {success_count}/{total_selected} nghiệp vụ được chọn!", 
                messages.SUCCESS
            )
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        from django.apps import apps
        try:
            DataSource = apps.get_model('app_miner', 'DataSource')
            project = DataSource.objects.first() 
            
            if project:
                extra_context['map_url'] = reverse('admin:project-map', args=[project.id])
            else:
                extra_context['map_url'] = '#' 
                self.message_user(request, "Anh Vũ ơi, nạp Project vào app_miner trước thì bản đồ mới chạy chuẩn được!", level='WARNING')
        except Exception as e:
            logger.error(f"Lỗi render map changelist view: {e}")

        return super().changelist_view(request, extra_context=extra_context)


# --- 4. Learning Log Admin (Giữ nguyên cấu hình Import/Export mượt mà) ---
class LearningLogResource(resources.ModelResource):
    project = fields.Field(column_name='project', attribute='project', widget=ForeignKeyWidget('app_miner.DataSource', 'name'))
    class Meta:
        model = LearningLog
        fields = ('id', 'project', 'question', 'admin_answer', 'is_learned')

@admin.register(LearningLog)
class LearningLogAdmin(ImportExportModelAdmin):
    resource_class = LearningLogResource
    list_display = ('project', 'question_short', 'admin_answer', 'is_learned', 'updated_at')
    list_editable = ('admin_answer', 'is_learned')
    list_filter = ('is_learned', 'project')
    search_fields = ('question', 'admin_answer')

    def question_short(self, obj):
        return (obj.question[:70] + "..") if len(obj.question) > 70 else obj.question
    question_short.short_description = "Câu hỏi AI"