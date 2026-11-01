from django.contrib import admin
from django.db import models
from .models import AIPromptConfig

@admin.register(AIPromptConfig)
class AIPromptConfigAdmin(admin.ModelAdmin):
    # 1. Hiển thị danh sách đẹp mắt
    list_display = (
        'name', 
        'module_code', 
        'function_code', 
        'provider_strategy', 
        'is_default', 
        'is_active', 
        'updated_at'
    )
    
    # 2. Bộ lọc thông minh
    list_filter = ('module_code', 'provider_strategy', 'is_active', 'is_default')
    
    # 3. Ô tìm kiếm
    search_fields = ('name', 'module_code', 'function_code', 'system_prompt')

    # 4. Tùy chỉnh giao diện soạn thảo Prompt cho "Chất"
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 15,
                'style': (
                    'font-family: "Fira Code", monospace; '
                    'background: #1e1e1e; color: #76EE00; '
                    'padding: 15px; border-radius: 5px;'
                )
            })
        },
    }
    
    # 5. Gom nhóm giao diện (Đã loại bỏ trường lỗi confidence_threshold)
    fieldsets = (
        ('📍 Định danh nghiệp vụ', {
            'fields': (('name', 'module_code'), ('function_code', 'is_default', 'is_active'))
        }),
        ('🧠 Nội dung & Hành vi AI', {
            'fields': ('system_prompt', 'temperature'),
            'description': 'Thiết lập "linh hồn" và cách AI phản hồi các yêu cầu từ hệ thống Kim Phát Hiệp Thành.'
        }),
        ('⚙️ Cấu hình Hạ tầng LLM', {
            'fields': (
                'provider_strategy', 
                'model_name', 
                'max_token_threshold',
                ('num_ctx', 'num_gpu_layers') # Các thông số cho Ollama/Local
            ),
            'description': 'Kiểm soát việc chọn Model Cloud (Groq/Gemini) hay Local (Ollama).'
        }),
    )

    # 6. Logic xử lý khi lưu
    def save_model(self, request, obj, form, change):
        # Nếu anh tích chọn "Mặc định", tự động tắt mặc định của các cấu hình khác cùng Module
        if obj.is_default:
            AIPromptConfig.objects.filter(
                module_code=obj.module_code, 
                is_default=True
            ).exclude(pk=obj.pk).update(is_default=False)
            
        super().save_model(request, obj, form, change)