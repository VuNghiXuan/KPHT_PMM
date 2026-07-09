# Trong apps/core/models.py
from apps.subscriptions.models import SubscriptionPlan
from django.db import models
from django.contrib.auth.models import User
from .middleware import get_current_company

class Company(models.Model):
    """
    Đại diện cho một đơn vị kinh doanh (Tenant).
    """
    name = models.CharField(max_length=255, verbose_name="Tên công ty")
    tax_code = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="Mã số thuế")
    plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Gói dịch vụ"
    )
    is_active = models.BooleanField(default=True, verbose_name="Trạng thái hoạt động")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Công ty"
        verbose_name_plural = "Các công ty"

    def __str__(self):
        return f"{self.name} ({self.tax_code})"

class CompanyManager(models.Manager):
    """
    Manager tự động lọc dữ liệu theo công ty đang đăng nhập.
    """
    def get_queryset(self):
        company = get_current_company()
        if company:
            return super().get_queryset().filter(company=company)
        return super().get_queryset().none()

class CompanyScopedModel(models.Model):
    """
    Abstract Model bắt buộc kế thừa cho mọi dữ liệu nghiệp vụ kế toán.
    """
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        verbose_name="Công ty sở hữu",
        db_index=True
    )

    class Meta:
        abstract = True

class Profile(models.Model):
    """
    Mở rộng thông tin User để gắn với một công ty cụ thể.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Người dùng", related_name="profile")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Công ty làm việc", related_name="members")
    
    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"

    def __str__(self):
        return f"{self.user.username} | {self.company.name}"