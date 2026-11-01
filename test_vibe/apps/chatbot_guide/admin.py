# apps/chatbot_guide/admin.py
import csv
import io
from django.contrib import admin, messages
from django.utils.html import format_html
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render, redirect
from .models import GuideCategory, GuideEntry

@admin.register(GuideCategory)
class GuideCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_display', 'order')
    list_editable = ('order',)
    search_fields = ('name',)
    
    actions = ['export_all_data_to_csv']

    def icon_display(self, obj):
        return format_html('<i class="fa {}" style="font-size: 18px;"></i> &nbsp; {}', obj.icon, obj.icon)
    icon_display.short_description = "Biểu tượng"

    # --- URL TÙY CHỈNH CHO IMPORT & CÀN QUÉT KIẾN TRÚC ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='category-import-csv'),
            path('generate-sys-map/', self.admin_site.admin_view(self.generate_system_map_view), name='generate-sys-map'),
        ]
        return custom_urls + urls

    # --- ĐẨY BIẾN RA NGOÀI GIAO DIỆN THANH CÔNG CỤ ADMIN ---
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['view_all_url'] = reverse('chatbot_guide:index')
        extra_context['show_import_button'] = True 
        extra_context['sys_map_url'] = reverse('admin:generate-sys-map')  # Nút bẻ luồng quét kiến trúc
        return super().changelist_view(request, extra_context=extra_context)

    # --- LOGIC TRIGGER CÀN QUÉT MÃ NGUỒN ---
    def generate_system_map_view(self, request):
        from .services import WikiAutoGenerator
        try:
            entry = WikiAutoGenerator.generate_system_map_lesson()
            self.message_user(
                request, 
                format_html("🚀 Đã càn quét toàn bộ mã nguồn! Bài học Wiki <b>'{}'</b> đã được đồng bộ mới nhất.", entry.title), 
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"💥 Thất bại khi quét kiến trúc: {str(e)}", messages.ERROR)
            
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/chatbot_guide/guidecategory/'))

    # --- LOGIC IMPORT CSV ---
    def import_csv_view(self, request):
        if request.method == "POST" and request.FILES.get("csv_file"):
            file = request.FILES["csv_file"]
            decoded_file = file.read().decode('utf-8-sig')
            reader = csv.reader(io.StringIO(decoded_file), delimiter=',', quotechar='"')
            
            try:
                next(reader)  # Bỏ qua header
            except StopIteration:
                pass

            count = 0
            for i, row in enumerate(reader, start=2):
                if len(row) < 4:
                    print(f"Bỏ qua dòng {i} do thiếu cột: {row}")
                    continue
                    
                try:
                    cat, _ = GuideCategory.objects.get_or_create(name=row[2].strip())
                    GuideEntry.objects.create(
                        order=row[0].strip(), 
                        title=row[1].strip(), 
                        category=cat, 
                        content=row[3].strip()
                    )
                    count += 1
                except Exception as e:
                    print(f"Lỗi tại dòng {i}: {e}")

            messages.success(request, f"Đã nhập thành công {count} mục!")
            return redirect("..")
        return render(request, "admin/chatbot_guide/guidecategory/csv_upload.html")

    # --- LOGIC EXPORT CSV ---
    def export_all_data_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=tat_ca_huong_dan.csv'
        writer = csv.writer(response)
        writer.writerow(['Order', 'Title', 'Category', 'Content'])
        
        entries = GuideEntry.objects.filter(category__in=queryset)
        for obj in entries:
            writer.writerow([obj.order, obj.title, obj.category.name, obj.content])
        return response
    export_all_data_to_csv.short_description = "Xuất toàn bộ bài viết của Danh mục đã chọn"


@admin.register(GuideEntry)
class GuideEntryAdmin(admin.ModelAdmin):
    list_display = ('order', 'title', 'category', 'is_reviewed', 'ai_gen_button')
    list_filter = ('category', 'is_reviewed')
    list_editable = ('is_reviewed',)
    search_fields = ('title', 'content', 'ai_notes', 'category__name', 'prerequisites')
    ordering = ('category', 'order')

    fieldsets = (
        ('Cấu hình AI Soạn bài', {'fields': ('ai_prompt_template', 'ai_notes')}),
        ('Thông tin cơ bản', {'fields': (('category', 'order', 'is_reviewed'), 'title')}),
        ('Nội dung hướng dẫn', {'fields': ('prerequisites', 'content', 'code_example', 'image_example')}),
    )

    def ai_gen_button(self, obj):
        return format_html(
            '<a class="button" href="{}" style="background: #1e7e34; color: white; padding: 2px 8px;">Gửi AI</a>',
            reverse('admin:guide-generate-ai', args=[obj.pk])
        )
    ai_gen_button.short_description = "AI Soạn"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/generate-ai/', self.admin_site.admin_view(self.generate_ai_view), name='guide-generate-ai'),
        ]
        return custom_urls + urls

    def generate_ai_view(self, request, pk):
        obj = self.get_object(request, pk)
        obj.content = f"--- NỘI DUNG AI SOẠN TỰ ĐỘNG ---\nYêu cầu: {obj.ai_notes}\n\n[Dữ liệu lập trình chi tiết...]"
        obj.is_reviewed = False
        obj.save()
        self.message_user(request, f"AI đã soạn xong bài: {obj.title}", messages.SUCCESS)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))