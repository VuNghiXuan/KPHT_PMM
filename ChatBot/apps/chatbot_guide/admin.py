from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import GuideCategory, GuideEntry

@admin.register(GuideCategory)
class GuideCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_display', 'order', 'view_on_site_link')
    list_editable = ('order',)
    search_fields = ('name',)

    def icon_display(self, obj):
        return format_html('<i class="fa {}" style="font-size: 18px;"></i> &nbsp; {}', obj.icon, obj.icon)
    icon_display.short_description = "Biểu tượng"

    def view_on_site_link(self, obj):
        # Dẫn về trang danh sách tổng hoặc bài đầu tiên của Category
        url = reverse('chatbot_guide:home') + f"?q={obj.name}"
        return format_html(
            '<a class="button" href="{}" target="_blank" '
            'style="padding: 5px 10px; background: #264b5d; color: #ffffff !important; '
            'border-radius: 4px; text-decoration: none; display: inline-block;">'
            'Xem Danh Mục</a>', 
            url
        )
    view_on_site_link.short_description = "Liên kết"

@admin.register(GuideEntry)
class GuideEntryAdmin(admin.ModelAdmin):
    # Loại bỏ view_on_site_link ở đây cho gọn theo ý anh
    list_display = ('order', 'title', 'category', 'updated_at')
    list_filter = ('category',)
    search_fields = ('title', 'content')
    ordering = ('category', 'order')
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': (('category', 'order'), 'title')
        }),
        ('Nội dung hướng dẫn', {
            'fields': ('prerequisites', 'content'),
        }),
        ('Ghi chú bổ sung', {
            'fields': ('future_notes',),
            'classes': ('collapse',),
        }),
    )