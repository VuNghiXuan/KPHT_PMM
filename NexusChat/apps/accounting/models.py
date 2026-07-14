# apps/accounting/models.py
from django.db import models
from apps.core.models import CompanyScopedModel, CompanyManager

class Voucher(CompanyScopedModel):
    """
    Model Chứng từ kế toán (Phiếu thu, phiếu chi, hóa đơn...).
    Kế thừa từ CompanyScopedModel để tự động phân tách dữ liệu theo công ty.
    """
    code = models.CharField(max_length=50, verbose_name="Số chứng từ")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Số tiền")
    date = models.DateField(verbose_name="Ngày chứng từ")
    description = models.TextField(blank=True, null=True, verbose_name="Diễn giải")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    # Gán Custom Manager để tự động lọc theo company
    objects = CompanyManager()

    class Meta:
        verbose_name = "Chứng từ"
        verbose_name_plural = "Các chứng từ"
        ordering = ['-date', '-created_at'] # Sắp xếp chứng từ mới nhất lên trước

    def __str__(self):
        return f"{self.code} - {self.amount}"