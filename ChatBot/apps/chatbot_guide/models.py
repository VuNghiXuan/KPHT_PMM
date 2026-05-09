from django.db import models
from django.urls import reverse

# Create your models here.


class GuideCategory(models.Model):
    name = models.CharField("Chủ đề lớn", max_length=100) # Ví dụ: Kiến thức Neo4j
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
    
    # Box nhắc nhở kiến thức
    prerequisites = models.TextField("Kiến thức cần có", blank=True, help_text="Cần nhớ gì trước khi đọc?")
    content = models.TextField("Nội dung chi tiết (HTML/Markdown)")
    
    # Box hướng tương lai
    future_notes = models.TextField("Mở rộng sau này", blank=True)
    
    order = models.FloatField("Thứ tự chèn", default=0.0, help_text="Dùng 1.1, 1.2 để chèn vào giữa")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "2. Bài viết chi tiết"
        verbose_name_plural = "2. Bài viết chi tiết"
        ordering = ['order']
    
    def get_absolute_url(self):
        # Trả về đường dẫn đến trang chi tiết bài học
        return reverse('chatbot_guide:detail', kwargs={'entry_id': self.pk})