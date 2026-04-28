from django.contrib import admin
from .models import BusinessTerm, BusinessProcess, IntentRouter

@admin.register(BusinessTerm)
class BusinessTermAdmin(admin.ModelAdmin):
    list_display = ('term', 'is_common', 'source_field')
    search_fields = ('term', 'definition', 'context')
    list_filter = ('is_common',)
    # Cho phép sửa nhanh ngay tại danh sách
    list_editable = ('is_common',)

@admin.register(BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'logic_rules')

@admin.register(IntentRouter)
class IntentRouterAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'intent_name', 'target_app', 'hit_count')
    search_fields = ('intent_name', 'display_name', 'keywords')
    list_filter = ('target_app',)
    # Sắp xếp theo số lần dùng nhiều nhất
    ordering = ('-hit_count',)