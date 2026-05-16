from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from .models import DataType

@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    # 1. Hiển thị danh sách trực quan
    list_display = ('name', 'code_badge', 'is_important_toggle', 'ai_preference_badge')
    search_fields = ('name', 'code')
    list_display = ('name', 'code_badge', 'is_important', 'ai_preference_badge') 
    list_editable = ('is_important',) # Cho phép bật/tắt nhanh trọng tâm nghiệp vụ

    # 2. Giao diện soạn thảo Prompt (Dark Mode - Monospace)
    # Giúp anh Vũ soi biến template {{...}} chính xác như đang dùng VS Code
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 15, 
                'style': (
                    'width: 95%; font-family: "Fira Code", "Consolas", monospace; '
                    'background: #1e1e1e; color: #d4d4d4; padding: 20px; '
                    'border-radius: 8px; border: 1px solid #333; line-height: 1.6; '
                    'tab-size: 4;'
                )
            })
        },
    }

    # 3. Phân nhóm thông tin logic (Fieldsets)
    fieldsets = (
        ('⚙️ Cấu hình chung', {
            'fields': (('name', 'code'), ('is_important', 'ai_model_preference')),
            'description': "Thiết lập định danh và mô hình AI ưu tiên cho loại dữ liệu này."
        }),
        ('🧠 Lò luyện AI (Prompt Engineering)', {
            'fields': ('system_prompt', 'user_prompt_template'),
            'description': format_html(
                "<div style='background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; color: #856404;'>"
                "<b>Mẹo:</b> Trong <i>User Prompt Template</i>, hãy sử dụng các biến: <br>"
                "<code style='color: #e83e8c;'>{{{{metadata}}}}</code>: Chứa dữ liệu Excel đã bóc tách.<br>"
                "<code style='color: #e83e8c;'>{{{{sheet_name}}}}</code>: Tên của Sheet đang xử lý."
                "</div>"
            )
        }),
    )

    # --- UI Helpers (Giúp anh nhìn nhanh trạng thái) ---
    def code_badge(self, obj):
        return format_html(
            '<code style="background: #e9ecef; padding: 2px 5px; border-radius: 3px; color: #d63384;">{}</code>',
            obj.code
        )
    code_badge.short_description = "Mã Miner"

    def is_important_toggle(self, obj):
        icon = "✅" if obj.is_important else "⚪"
        return format_html('<span style="font-size: 16px;">{}</span>', icon)
    is_important_toggle.short_description = "Trọng tâm"

    def ai_preference_badge(self, obj):
        color = "#6f42c1" if obj.ai_model_preference == 'GROQ' else "#0d6efd"
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, obj.ai_model_preference
        )
    ai_preference_badge.short_description = "Ưu tiên"

    # 4. Hướng dẫn nhanh trong Form
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context.update({
            'help_text': "Ứng Dụng Vàng-Coach: Hãy nhớ định nghĩa vai trò 'Chuyên gia tiệm vàng' để AI có tone-of-voice chuẩn nhất."
        })
        return super().render_change_form(request, context, add, change, form_url, obj)