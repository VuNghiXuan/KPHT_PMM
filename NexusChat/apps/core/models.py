# apps/core/models.py
"""
Định nghĩa các Model nền tảng cho hệ thống Multi-tenant: User, Company và Profile.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from apps.subscriptions.models import SubscriptionPlan
from .middleware import get_current_company

class User(AbstractUser):
    # Ghi đè quan hệ groups
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="core_user_set", # Thay đổi related_name tại đây
        related_query_name="user",
    )
    
    # Ghi đè quan hệ user_permissions
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="core_user_set", # Thay đổi related_name tại đây
        related_query_name="user",
    )

    class Meta:
        verbose_name = "Người dùng"
        verbose_name_plural = "Người dùng"

    @property
    def has_profile(self):
        """
        Kiểm tra người dùng đã có liên kết Profile chưa.
        Returns: bool: True nếu đã có profile.
        """
        return hasattr(self, 'profile')

class Company(models.Model):
    """
    Đại diện cho một đơn vị kinh doanh (Tenant).
    """
    name = models.CharField(max_length=255, verbose_name="Tên công ty")
    tax_code = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="Mã số thuế")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, verbose_name="Gói dịch vụ")
    is_active = models.BooleanField(default=True, verbose_name="Trạng thái hoạt động")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Công ty"
        verbose_name_plural = "Công ty"

    def __str__(self):
        return f"{self.name} ({self.tax_code})"

class CompanyManager(models.Manager):
    """
    Manager tự động lọc dữ liệu theo công ty đang đăng nhập qua Middleware.
    """
    def get_queryset(self):
        company = get_current_company()
        if company:
            return super().get_queryset().filter(company=company)
        return super().get_queryset().none()

class CompanyScopedModel(models.Model):
    """
    Abstract Model bắt buộc kế thừa cho mọi dữ liệu nghiệp vụ kế toán (Chứng từ, Sổ cái).
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Công ty sở hữu")
    objects = CompanyManager() # Áp dụng manager lọc theo tenant

    class Meta:
        abstract = True

class Profile(models.Model):
    """
    Mở rộng thông tin người dùng gắn với công ty.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="profile"
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="members")
    
    
    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"

    def __str__(self):
        return f"{self.user.username} - {self.company.name}"