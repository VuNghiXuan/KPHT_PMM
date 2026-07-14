"""
File: apps/subscriptions/admin.py
Mô tả: Cấu hình giao diện Admin cho các gói dịch vụ và đăng ký công ty.
"""
from django.contrib import admin
from .models import Feature, SubscriptionPlan, CompanySubscription

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'get_features') # Thêm price vào danh sách hiển thị
    list_editable = ('price',) # Cho phép sửa giá nhanh ngay tại bảng danh sách
    filter_horizontal = ('features',)

    def get_features(self, obj):
        return ", ".join([f.name for f in obj.features.all()])
    get_features.short_description = 'Tính năng bao gồm'

@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('company', 'plan', 'start_date', 'is_active')
    list_filter = ('plan', 'is_active')
    search_fields = ('company__name', 'company__tax_code')
    # Cho phép chọn công ty qua popup (tránh load danh sách quá dài)
    raw_id_fields = ('company',)