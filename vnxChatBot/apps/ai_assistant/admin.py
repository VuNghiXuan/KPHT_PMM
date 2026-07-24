from django.contrib import admin
from .models import GroupAIProvider

@admin.register(GroupAIProvider)
class GroupAIProviderAdmin(admin.ModelAdmin):
    list_display = ('group', 'provider', 'model_name', 'has_custom_api_key')
    list_filter = ('provider',)
    search_fields = ('group__name', 'model_name')
    
    @admin.display(boolean=True, description="Có API Key riêng")
    def has_custom_api_key(self, obj):
        """Kiểm tra xem nhóm có cấu hình API Key riêng hay đang dùng key chung hệ thống."""
        return bool(obj.api_key)