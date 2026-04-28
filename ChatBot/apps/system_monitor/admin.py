from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.contrib import messages
from .models import DataType, ProjectStructure, IntentStore, KnowledgeExchange
from django.utils.html import format_html

@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_ai_generated', 'confidence_score')
    search_fields = ('name', 'code')


@admin.register(ProjectStructure)
class ProjectStructureAdmin(admin.ModelAdmin):
    # Hiển thị: Tên (thụt lề), Loại, Đường dẫn, Trạng thái
    list_display = ('display_name', 'obj_type', 'path', 'is_active', 'last_updated')
    list_filter = ('obj_type', 'is_active')
    search_fields = ('name', 'path', 'docstring')
    
    # Giữ nguyên nút đồng bộ xịn sò của anh em mình
    change_list_template = "admin/project_structure_changelist.html"

    def display_name(self, obj):
        """Tạo hiệu ứng nhánh cây bằng cách thụt lề CSS"""
        margin = obj.level * 25  # Mỗi cấp thụt vào 25px
        
        # Chọn icon cho đẹp lão
        icon = "📁" if obj.obj_type == 'FILE' else "📦" if obj.obj_type == 'CLASS' else "⚡"
        
        # Nếu là hàm thì cho chữ nhỏ lại chút nhìn cho rõ phân cấp
        font_weight = "bold" if obj.obj_type in ['FILE', 'CLASS'] else "normal"
        color = "#264b5d" if obj.obj_type == 'FILE' else "#444"

        return format_html(
            '<span style="margin-left:{}px; font-weight:{}; color:{}">{} {}</span>',
            margin, font_weight, color, icon, obj.name
        )
    display_name.short_description = "Cấu trúc nhánh cây"

    # --- PHẦN LOGIC CỦA NÚT ĐỒNG BỘ ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync-code/', self.admin_site.admin_view(self.sync_view), name='sync-code-structure'),
        ]
        return custom_urls + urls

    def sync_view(self, request):
        try:
            ProjectStructure.sync_project_structure()
            self.message_user(request, "Đã quét và dựng xong bản đồ nhánh cây!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Lỗi quét code: {e}", messages.ERROR)
        return redirect("..")

@admin.register(IntentStore)
class IntentStoreAdmin(admin.ModelAdmin):
    list_display = ('user_query', 'detected_intent', 'is_correct', 'created_at')
    list_editable = ('is_correct',)
    readonly_fields = ('response_logic',) # Logic của AI để xem thôi, đừng sửa

@admin.register(KnowledgeExchange)
class KnowledgeExchangeAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'action_type', 'status', 'timestamp')
    list_filter = ('action_type', 'status')