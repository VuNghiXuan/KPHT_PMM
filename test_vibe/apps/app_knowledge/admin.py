from django.contrib import admin, messages
from django.db import models
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils import timezone
from django.utils.safestring import mark_safe
import json

from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .services import KnowledgeService
from .models import LearningLog, KnowledgeDraft
# from apps.app_ai_core.models import AIPromptConfig # Thêm import này
from .views import agent_workflow_map

@admin.register(KnowledgeDraft)
class KnowledgeDraftAdmin(admin.ModelAdmin):
    """
    HTJ Knowledge Hub - Nơi anh Vũ kiểm soát tri thức từ AI
    """
    list_display = ('id', 'term', 'display_sheet', 'data_type', 'colored_status', 'ai_actions','view_map_button')
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
                    'font-size: 14px; ' # THÊM DÒNG NÀY VÀO
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
            'description': mark_safe("<b style='color:#ffa000;'>Lưu ý:</b> Lưu tại đây sẽ cập nhật trực tiếp vào Excel Sheet.")
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
                # Lấy Model động từ hệ thống thay vì import trực tiếp ở đầu file
                AIPromptConfig = apps.get_model('app_ai_core', 'AIPromptConfig')
                
                # Tìm cấu hình AI tương ứng với mã Module (DataType code)
                config = AIPromptConfig.objects.filter(
                    module_code=obj.data_type.code, 
                    is_active=True
                ).first()

                if config:
                    # Tạo URL dẫn đến trang chỉnh sửa cấu hình đó
                    url = reverse('admin:app_ai_core_aipromptconfig_change', args=[config.pk])
                    return mark_safe(
                        f'<a href="{url}" target="_blank" style="color: #ffa000; font-weight: bold;">'
                        f'⚙️ Sửa Prompt cho {obj.data_type.name}</a>'
                    )
            except (LookupError, Exception):
                # Phòng trường hợp app chưa migrate hoặc model chưa tồn tại
                pass
                
        return "Đang dùng cấu hình AI mặc định"

    edit_datatype_link.short_description = "Cấu hình AI"

    def colored_status(self, obj):
        colors = {'PENDING': '#7f8c8d', 'AI_READY': '#2980b9', 'EDITED': '#e67e22', 'FINAL': '#27ae60'}
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
        Ghi đè phương thức save của Admin để đồng bộ sang app_miner
        """
        super().save_model(request, obj, form, change)
        
        # Nếu Anh Vũ sửa xong và Lưu, tự động đẩy mô tả về Sheet gốc
        if obj.status in ['EDITED', 'FINAL'] and obj.sheet:
            obj.sheet.description = obj.content
            obj.sheet.save()
            self.message_user(request, f"Đã đồng bộ tri thức vào Sheet: {obj.sheet.name}")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/refine/', self.admin_site.admin_view(self.run_ai_refine), name='ai-refine'),
            path('<int:object_id>/export/', self.admin_site.admin_view(self.export_single_json), name='knowledge-export'),
            path('<int:project_id>/map/', self.admin_site.admin_view(agent_workflow_map), name='project-map'),
        ]
        return custom_urls + urls

    def view_map_button(self, obj):
        # Kiểm tra nếu draft có gắn với project thì mới hiện link
        if obj.project:
            url = reverse('admin:project-map', args=[obj.project.id])
            return format_html('<a class="button" href="{}">🗺️ Xem sơ đồ</a>', url)
        return "N/A"
    view_map_button.short_description = "Bản đồ"
    
    def run_ai_refine(self, request, object_id):
        success = KnowledgeService.refine_draft(object_id)
        if success:
            self.message_user(request, "AI đã hoàn thành tinh chế!", messages.SUCCESS)
        else:
            self.message_user(request, "AI lỗi. Kiểm tra cấu hình Prompt hoặc Log.", messages.ERROR)
        return redirect('admin:app_knowledge_knowledgedraft_changelist')

    def export_single_json(self, request, object_id):
        obj = self.get_object(request, object_id)
        data = {'term': obj.term, 'content': obj.content, 'metadata': obj.origin_metadata, 'date': str(timezone.now())}
        response = HttpResponse(json.dumps(data, indent=4, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="HTJ_{obj.id}.json"'
        return response

    actions = ['refine_full_project']

    @admin.action(description="🚀 CHẠY TOÀN BỘ PROJECT (Càn quét AI)")
    def refine_full_project(self, request, queryset):
        first = queryset.first()
        if not first or not first.project: return
        
        count = KnowledgeService.refine_all_project_drafts(first.project.id)
        self.message_user(request, f"Đã xử lý xong {count} nghiệp vụ cho dự án {first.project.name}", messages.SUCCESS)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        from django.apps import apps
        try:
            DataSource = apps.get_model('app_miner', 'DataSource')
            project = DataSource.objects.first() 
            
            if project:
                extra_context['map_url'] = reverse('admin:project-map', args=[project.id])
            else:
                # Nếu chưa có project, anh cho nó cái link tạm hoặc link báo lỗi
                extra_context['map_url'] = '#' 
                self.message_user(request, "Anh Vũ ơi, nạp Project vào app_miner trước thì bản đồ mới chạy chuẩn được!", level='WARNING')
        except Exception as e:
            print(f"DEBUG: Lỗi: {e}")

        return super().changelist_view(request, extra_context=extra_context)

# --- 4. Learning Log Admin ---
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