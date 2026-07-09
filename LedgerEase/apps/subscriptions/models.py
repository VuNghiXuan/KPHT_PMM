# apps/subscriptions/models.py
"""
Đây là nơi định nghĩa các gói dịch vụ (ví dụ: Miễn phí, Nâng cao, Doanh nghiệp).
"""

from django.db import models

class Feature(models.Model):
    """Định nghĩa các App/Tính năng trong hệ thống."""
    name = models.CharField(max_length=100, verbose_name="Tên tính năng")
    slug = models.SlugField(unique=True, verbose_name="Mã định danh")

    class Meta:
        verbose_name = "Tính năng (App)"
        verbose_name_plural = "Các tính năng"

    def __str__(self):
        return self.name

class SubscriptionPlan(models.Model):
    """Các gói dịch vụ."""
    name = models.CharField(max_length=100, verbose_name="Tên gói")
    features = models.ManyToManyField(Feature, verbose_name="Các tính năng được cấp")
    
    class Meta:
        verbose_name = "Gói dịch vụ"
        verbose_name_plural = "Các gói dịch vụ"

    def __str__(self):
        return self.name