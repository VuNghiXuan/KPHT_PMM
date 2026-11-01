# app_ai_core/admin.py
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from .models import AIPromptConfig, AITokenLog

@admin.register(AIPromptConfig)
class AIPromptConfigAdmin(admin.ModelAdmin):
    # giữ nguyên bộ cấu hình "Chất" của anh Vũ ở đây...
    list_display = ('name', 'module_code', 'function_code', 'provider_strategy', 'is_default', 'is_active', 'updated_at')
    list_filter = ('module_code', 'provider_strategy', 'is_active', 'is_default')
    search_fields = ('name', 'module_code', 'function_code', 'system_prompt')
    
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 15,
                'style': 'font-family: "Fira Code", monospace; background: #1e1e1e; color: #76EE00; padding: 15px; border-radius: 5px;'
            })
        },
    }
    
    fieldsets = (
        ('📍 Định danh nghiệp vụ', {
            'fields': (('name', 'module_code'), ('function_code', 'is_default', 'is_active'))
        }),
        ('🧠 Nội dung & Hành vi AI', {
            'fields': ('system_prompt', 'temperature'),
            'description': 'Thiết lập "linh hồn" và cách AI phản hồi các yêu cầu từ hệ thống Ứng Dụng Vàng.'
        }),
        ('⚙️ Cấu hình Hạ tầng LLM', {
            'fields': ('provider_strategy', 'model_name', 'max_token_threshold', ('num_ctx', 'num_gpu_layers')),
            'description': 'Kiểm soát việc chọn Model Cloud (Groq/Gemini) hay Local (Ollama).'
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            AIPromptConfig.objects.filter(
                module_code=obj.module_code, 
                is_default=True
            ).exclude(pk=obj.pk).update(is_default=False)
        super().save_model(request, obj, form, change)


@admin.register(AITokenLog)
class AITokenLogAdmin(admin.ModelAdmin):
    """
    Dashboard giám sát thời gian thực rổ API Keys Cloud Free
    """
    # 1. Hiển thị thông số dạng bảng điều khiển
    list_display = (
        'key_name', 
        'provider', 
        'status_badge',         # Biểu tượng trạng thái trực quan
        'requests_progress',    # Tiến độ số lượt gọi (Đã dùng / Hạn mức)
        'tokens_usage_display', # Tổng lượng token đã tiêu thụ
        'last_used'
    )
    
    list_filter = ('provider', 'is_active')
    search_fields = ('key_name', 'api_key', 'reason_blocked')
    ordering = ('provider', 'requests_today')
    
    # 2. Phân nhóm quản lý hạn ngạch rõ ràng
    fieldsets = (
        ('🛡️ Cấu hình định danh Key', {
            'fields': ('key_name', 'provider', 'api_key', 'is_active')
        }),
        ('📊 Hạn ngạch Free Tier & Thống kê hôm nay', {
            'fields': (
                ('daily_request_limit', 'requests_today'),
                ('daily_token_limit', 'tokens_sent_today', 'tokens_received_today')
            ),
            'description': 'Hệ thống tự động theo dõi và đối chiếu các thông số này để ra quyết định hạ tải (Smart Fallback).'
        }),
        ('📝 Nhật ký hệ thống', {
            'fields': ('reason_blocked',),
            'classes': ('collapse',) # Ẩn bớt đi, khi nào cần mới bấm mở rộng ra
        }),
    )

    # 3. Custom hiển thị cột trạng thái dạng Badge màu cho dễ nhìn (Xanh / Đỏ)
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #26a69a; font-weight: bold;">🟢 Hoạt động</span>')
        return format_html('<span style="color: #ef5350; font-weight: bold;">🔴 Khóa tạm thời</span>')
    status_badge.short_description = "Trạng thái"

    # 4. Hiển thị tiến độ sử dụng lượt gọi dưới dạng text trực quan
    def requests_progress(self, obj):
        ratio = (obj.requests_today / obj.daily_request_limit) * 100
        color = "#26a69a" if ratio < 80 else "#ffa726" if ratio < 95 else "#ef5350"
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}/{} rq</span> ({:.1f}%)', 
            color, obj.requests_today, obj.daily_request_limit, ratio
        )
    requests_progress.short_description = "Số cuộc gọi hôm nay"

    # 5. Gom thông số token gộp lại thành 1 cột để tiết kiệm không gian màn hình
    def tokens_usage_display(self, obj):
        total = obj.tokens_sent_today + obj.tokens_received_today
        return format_html(
            '<span>Sent: <b>{:,}</b></span><br><span style="color:#666;">Recv: <b>{:,}</b></span><br><span>Tổng: {:,}</span>',
            obj.tokens_sent_today, obj.tokens_received_today, total
        )
    tokens_usage_display.short_description = "Lượng Token tiêu thụ"

    # 6. ACTION THỦ CÔNG: Cho phép anh Vũ chọn các Key và "Kích hoạt lại hạn ngạch" lập tức
    actions = ['force_reset_quota']

    @admin.action(description='🔄 Reset hạn ngạch hôm nay (Thủ công)')
    def force_reset_quota(self, request, queryset):
        rows_updated = queryset.update(
            requests_today=0,
            tokens_sent_today=0,
            tokens_received_today=0,
            is_active=True,
            reason_blocked=None
        )
        self.message_user(request, f"✨ Đã reset sạch sẽ dữ liệu sử dụng cho {rows_updated} API Keys thành công!")