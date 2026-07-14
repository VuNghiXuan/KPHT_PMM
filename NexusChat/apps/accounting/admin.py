from django.contrib import admin
from .models import Voucher

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    """
    Cấu hình hiển thị Chứng từ trong Admin.
    Tự động lọc dữ liệu theo công ty của Admin đang đăng nhập.
    """
    list_display = ('code', 'date', 'amount', 'company')
    list_filter = ('date', 'company')
    search_fields = ('code', 'description')

    def get_queryset(self, request):
        """
        Đảm bảo Admin chỉ nhìn thấy dữ liệu của công ty họ được phép truy cập.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.profile.company)