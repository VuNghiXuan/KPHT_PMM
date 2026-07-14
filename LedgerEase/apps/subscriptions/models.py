"""
File: apps/subscriptions/models.py
Mô tả: Quản lý các gói dịch vụ, tính năng và đăng ký sử dụng của các Tenant (Công ty).
Tác giả: LedgerEase Engineering Team
Liên kết: 
    - apps.core.models (Company)
"""

from django.db import models

class Feature(models.Model):
    """
    Đại diện cho một tính năng/module cụ thể trong hệ thống.
    Ví dụ: 'Báo cáo tài chính', 'Quản lý kho'.
    """
    name = models.CharField(max_length=100, verbose_name="Tên tính năng")
    slug = models.SlugField(unique=True, verbose_name="Mã định danh (Slug)")

    class Meta:
        verbose_name = "Tính năng"
        verbose_name_plural = "Các tính năng"

    def __str__(self):
        return self.name

class SubscriptionPlan(models.Model):
    """
    Định nghĩa các gói dịch vụ thương mại.
    """
    name = models.CharField(max_length=100, verbose_name="Tên gói")
    slug = models.SlugField(unique=True, verbose_name="Mã gói (Slug)")
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        verbose_name="Giá tiền (VNĐ/tháng)",
        help_text="Số tiền khách hàng phải trả hàng tháng."
    )
    description = models.TextField(verbose_name="Mô tả chi tiết", help_text="Mô tả ngắn gọn về gói dịch vụ.")
    features = models.ManyToManyField(Feature, verbose_name="Tính năng bao gồm")
    
    class Meta:
        verbose_name = "Gói dịch vụ"
        verbose_name_plural = "Các gói dịch vụ"

    def __str__(self):
        return f"{self.name} - {self.price:,.0f} VNĐ"

class CompanySubscription(models.Model):
    """
    Bản ghi liên kết Công ty với Gói dịch vụ đã đăng ký.
    """
    company = models.OneToOneField(
        'core.Company',
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="Công ty"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        verbose_name="Gói dịch vụ hiện tại"
    )
    start_date = models.DateField(auto_now_add=True, verbose_name="Ngày đăng ký")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")

    class Meta:
        verbose_name = "Đăng ký dịch vụ công ty"
        verbose_name_plural = "Đăng ký dịch vụ công ty"

    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"