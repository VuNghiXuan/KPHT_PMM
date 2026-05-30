from django.db import models
from django.urls import reverse

class GuideCategory(models.Model):
    name = models.CharField("Chủ đề lớn", max_length=100)
    icon = models.CharField("Icon (FontAwesome)", max_length=50, default="fa-book")
    order = models.FloatField("Thứ tự", default=0.0)

    class Meta:
        verbose_name = "1. Nhóm Hướng dẫn"
        verbose_name_plural = "1. Nhóm Hướng dẫn"
        ordering = ['order']

    def __str__(self):
        return self.name

class GuideEntry(models.Model):
    category = models.ForeignKey(GuideCategory, on_delete=models.CASCADE, related_name='entries')
    title = models.CharField("Tiêu đề bài học", max_length=200)
    
    # --- PHẦN AI SOẠN THẢO ---
    ai_prompt_template = models.TextField("Prompt mẫu (System)", blank=True, 
        help_text="Cấu trúc lệnh để AI dựa vào soạn bài.")
    ai_notes = models.TextField("Ghi chú bắt buộc cho AI", blank=True, 
        help_text="Yêu cầu riêng cho bài này, AI không được bỏ qua.")
    is_reviewed = models.BooleanField("Đã duyệt nội dung", default=False, 
        help_text="Chỉ những bài đã duyệt mới hiển thị cho người dùng.")

    # --- NỘI DUNG CHI TIẾT ---
    prerequisites = models.TextField("Kiến thức cần có", blank=True)
    content = models.TextField("Nội dung chi tiết (HTML/Markdown)")
    code_example = models.TextField("Mã code ví dụ (Cypher/Python)", blank=True)
    image_example = models.ImageField("Hình ảnh minh họa", upload_to="guides/images/", blank=True, null=True)
    
    future_notes = models.TextField("Mở rộng sau này", blank=True)
    order = models.FloatField("Thứ tự chèn", default=0.0)

    is_system_generated = models.BooleanField("Bài viết hệ thống tự động", default=False)
    system_app_label = models.CharField("App liên quan", max_length=50, blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "2. Bài viết chi tiết"
        verbose_name_plural = "2. Bài viết chi tiết"
        ordering = ['order']
    
    def get_absolute_url(self):
        return reverse('chatbot_guide:detail', kwargs={'entry_id': self.pk})