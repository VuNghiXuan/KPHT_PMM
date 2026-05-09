from django.contrib import admin, messages
from django.db import models
from django.urls import path
from django.shortcuts import redirect, render
from django.utils.html import format_html
import json

# CHỈ IMPORT những gì thực sự có trong models.py
from .models import KnowledgeDraft

# --- 1. QUẢN LÝ BẢN THẢO TRI THỨC (Trung tâm điều hành HTJ) ---

@admin.register(KnowledgeDraft)
class KnowledgeDraftAdmin(admin.ModelAdmin):
    """
    Dòng chảy: Miner -> Draft (Duyệt tại đây) -> Chốt -> Agent sử dụng.
    """
    list_display = ('id', 'term', 'category', 'project', 'colored_status', 'ai_execution_hub')
    
    list_filter = ('category', 'status', 'project')
    search_fields = ('term', 'content')
    
    # Giao diện gõ code cho đẹp để anh soi logic vàng
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={
                'rows': 12, 
                'style': 'width: 100%; font-family: "Consolas", monospace; background: #fdf6e3;'
            })
        },
    }

    fieldsets = (
        ('📌 Thông tin cơ bản', {
            'fields': (('term', 'category'), 'project', 'status')
        }),
        ('🤖 Nội dung tri thức (Markdown/Logic)', {
            'fields': ('content',),
        }),
        ('🛠️ Dữ liệu gốc từ Excel', {
            'classes': ('collapse',),
            'fields': ('origin_metadata',),
        }),
    )
    
    readonly_fields = ('origin_metadata',)

    # --- UI Helpers ---
    def colored_status(self, obj):
        # Kiểm tra xem trạng thái có tồn tại không
        status = obj.status if obj.status else "PENDING"
        
        # Định nghĩa bảng màu (Nên dùng dict.get để tránh lỗi None)
        colors = {
            'DRAFT': '#9e9e9e',      # Xám
            'REVIEWING': '#ff9800',  # Cam
            'PUBLISHED': '#4caf50',  # Xanh lá
            'REJECTED': '#f44336',   # Đỏ
        }
        
        # Lấy màu, nếu không có trong danh sách thì mặc định màu đen
        color = colors.get(status, '#000000')
        
        # Trả về HTML an toàn
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display() if hasattr(obj, 'get_status_display') else status
        )
    colored_status.short_description = "Trạng thái"

    def ai_execution_hub(self, obj):
        if obj.status == 'APPROVED':
            return format_html('<span style="color: #00AB66;">✅ Đã nạp Graph</span>')
        
        # Nút chốt nhanh trạng thái
        btn_approve = format_html(
            '<a class="button" style="background: #28a745;" href="./{}/approve/">✔️ Duyệt</a>', obj.pk
        )
        return btn_approve

    # --- Logic Custom Actions ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/approve/', self.admin_site.admin_view(self.approve_draft), name='knowledge-approve'),
        ]
        return custom_urls + urls

    def approve_draft(self, request, object_id):
        draft = self.get_object(request, object_id)
        draft.status = 'APPROVED'
        draft.save()
        self.message_user(request, f"Đã duyệt tri thức: {draft.term}")
        return redirect('admin:ai_knowledge_knowledgedraft_changelist')