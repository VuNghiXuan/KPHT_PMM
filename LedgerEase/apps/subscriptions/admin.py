from django.contrib import admin
from .models import Feature, SubscriptionPlan

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    # Cấu hình nhãn cho trang chỉnh sửa chi tiết
    fieldsets = (
        ('Thông tin tính năng', {
            'fields': ('name', 'slug')
        }),
    )

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_features')
    filter_horizontal = ('features',)

    def get_features(self, obj):
        return ", ".join([f.name for f in obj.features.all()])
    
    # Đặt nhãn tiếng Việt cho cột hàm hiển thị
    get_features.short_description = 'Danh sách tính năng'