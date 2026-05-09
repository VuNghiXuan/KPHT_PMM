from django.db import models

class KnowledgeDraft(models.Model):
    # Dùng string import để tránh lỗi vòng lặp (circular import)
    project = models.ForeignKey('app_miner.ExcelProject', on_delete=models.CASCADE, null=True, blank=True)
    term = models.CharField("Thuật ngữ/Logic", max_length=255)
    category = models.CharField(max_length=50, choices=[('LOGIC', 'Logic'), ('TERM', 'Từ điển')])
    content = models.TextField("Mô tả chi tiết cho AI")
    status = models.CharField(max_length=20, default='PENDING')
    origin_metadata = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bản thảo tri thức"
        verbose_name_plural = "Bản thảo tri thức"