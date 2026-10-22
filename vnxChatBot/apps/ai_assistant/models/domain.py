# apps\ai_assistant\models\domain.py
from django.db import models

class DomainCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên phân hệ")
    code = models.SlugField(unique=True, verbose_name="Mã định danh")
    description = models.TextField(
        help_text="Mô tả phạm vi nghiệp vụ dùng để AI tính Cosine Similarity."
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name="Phân hệ cha"
    )
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")
    similarity_threshold = models.FloatField(
        default=0.60, 
        verbose_name="Ngưỡng độ tương đồng tối thiểu"
    )
    # 🌟 Lưu sẵn Vector đại diện dạng mảng [0.12, -0.45, ...]
    embedding = models.JSONField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Danh mục Phân hệ"
        verbose_name_plural = "Danh sách Phân hệ"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} ➔ {self.name}"
        return self.name

    def get_full_text(self):
        """Gộp tên và mô tả để tạo ngữ cảnh hoàn chỉnh nhất cho AI"""
        return f"{self.name}: {self.description}"