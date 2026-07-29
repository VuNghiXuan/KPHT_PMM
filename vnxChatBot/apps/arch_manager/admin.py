"""
Module: arch_manager.admin
Author: Senior Software Engineer & Architecture Lead
Description: Cấu hình hiển thị và quản lý model SystemBlueprint trong trang Django Admin.
             Tích hợp liên kết nhanh tới giao diện Living Documentation trực quan.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import SystemBlueprint
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html


@admin.register(SystemBlueprint)
class SystemBlueprintAdmin(admin.ModelAdmin):
    """
    Tùy chỉnh giao diện quản trị cho SystemBlueprint, giúp quản trị viên 
    kiểm soát các phiên bản tài liệu kiến trúc.
    """
    list_display = ('version', 'title', 'is_active', 'view_architecture_btn', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('version', 'title', 'description')
    readonly_fields = ('created_at', 'view_architecture_readonly')
    
    fieldsets = (
        ("Thông tin chung", {
            'fields': ('version', 'title', 'description', 'is_active', 'view_architecture_readonly')
        }),
        ("Mã nguồn Sơ đồ Mermaid (Tự động hoặc tùy chỉnh)", {
            'fields': ('code_flow_mermaid', 'erd_mermaid', 'state_machine_mermaid', 'component_mermaid'),
            'classes': ('collapse',)
        }),
        ("Hệ thống", {
            'fields': ('created_at',)
        }),
    )

    # def view_architecture_btn(self, obj):
    #     """Tạo nút bấm mở trang Living Documentation ngoài danh sách admin."""
    #     url = reverse('arch_manager:blueprint_dashboard')
    #     return format_html(
    #         '<a class="button" href="{}" target="_blank" style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none;">🚀 Xem Giao Diện Sơ Đồ</a>',
    #         url
    #     )
    # view_architecture_btn.short_description = "Living Doc"

    def view_architecture_btn(self, obj):
        """Tạo nút bấm mở trang Living Documentation ngoài danh sách admin an toàn."""
        try:
            url = reverse('arch_manager:blueprint_dashboard')
        except NoReverseMatch:
            url = '#'
        
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none;">🚀 Xem Giao Diện Sơ Đồ</a>',
            url
        )
    view_architecture_btn.short_description = "Living Doc"

    def view_architecture_readonly(self, obj):
        """Tạo nút bấm mở trang Living Documentation trong form chi tiết."""
        url = reverse('arch_manager:blueprint_dashboard')
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color: #007bff; color: white; padding: 6px 14px; border-radius: 4px; text-decoration: none; font-weight: bold;">🔍 Mở Kho Sơ Đồ Trực Quan (4 Tabs)</a>',
            url
        )
    view_architecture_readonly.short_description = "Trang Sơ Đồ Trực Quan"

    def save_model(self, request, obj, form, change):
        """Đảm bảo chỉ có 1 bản ghi active tại một thời điểm."""
        if obj.is_active:
            SystemBlueprint.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)