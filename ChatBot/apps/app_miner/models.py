import os, logging
from django.db import models, transaction
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class ExcelProject(models.Model):
    """
    Quản lý file Excel tổng. Đây là điểm khởi đầu, ví dụ: 'Báo cáo KPHT Tháng 4'.
    """
    name = models.CharField("Tên Dự Án/Tiệm Vàng", max_length=255, db_index=True)
    file_path = models.FileField("File Excel Gốc", upload_to='excels/%Y/%m/')
    status = models.CharField(
        "Trạng thái", 
        max_length=20, 
        default='PENDING', 
        choices=[
            ('PENDING', 'Chờ xử lý'), 
            ('PROCESSING', 'Đang bóc tách'), 
            ('COMPLETED', 'Hoàn tất'), 
            ('FAILED', 'Lỗi hệ thống')
        ]
    )
    uploaded_at = models.DateTimeField("Ngày tải lên", auto_now_add=True)

    class Meta:
        verbose_name = "1. Dự án Excel"
        verbose_name_plural = "1. Dự án Excel"

    def __str__(self):
        # Hiển thị tên dự án kèm trạng thái trên Admin
        return f"{self.name} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Sau khi lưu file thành công, kích hoạt nhạc trưởng bóc tách dữ liệu
            transaction.on_commit(lambda: self.automate_workflow())

    def automate_workflow(self):
        try:
            from .excel_miner import ExcelMinerService
            ExcelMinerService.run_workflow(self)
        except Exception as e:
            logger.error(f"Lỗi khởi động Orchestrator cho dự án {self.name}: {str(e)}")

class ExcelSheet(models.Model):
    """
    Lưu thông tin từng Sheet riêng lẻ (VD: Sheet 'Mua Vào', 'Bán Ra').
    """
    project = models.ForeignKey(ExcelProject, on_delete=models.CASCADE, related_name='sheets', verbose_name="Dự án")
    name = models.CharField("Tên Sheet", max_length=255)
    category = models.CharField("Phân loại nghiệp vụ", max_length=100, blank=True, null=True, help_text="VD: Thu mua, Cầm đồ...")

    class Meta:
        verbose_name = "2. Danh mục Sheet"
        verbose_name_plural = "2. Danh mục Sheet"

    def __str__(self):
        return f"Sheet: {self.name} (Dự án: {self.project.name})"

class ExcelTableRegion(models.Model):
    """
    Xác định các vùng dữ liệu trong Sheet (VD: Vùng A1:D10 là thông tin khách hàng).
    """
    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='regions', verbose_name="Sheet")
    name = models.CharField("Tên Vùng", max_length=255)
    coordinates = models.CharField("Tọa độ (Range)", max_length=50, help_text="Ví dụ: A1:M20")
    region_type = models.CharField("Loại vùng", max_length=50, default='FORM', help_text="FORM (nhập liệu) hoặc LIST (danh sách)")

    class Meta:
        verbose_name = "3. Vùng Nghiệp Vụ"
        verbose_name_plural = "3. Vùng Nghiệp Vụ"

    def __str__(self):
        return f"{self.name} [{self.coordinates}] - {self.sheet.name}"

class DataField(models.Model):
    """
    Lưu chi tiết từng ô Excel (Địa chỉ, Giá trị, Công thức).
    Đây là 'nguyên tử' tri thức để Agent học.
    """
    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='fields', verbose_name="Sheet")
    region = models.ForeignKey(ExcelTableRegion, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vùng dữ liệu")
    cell_address = models.CharField("Địa chỉ ô", max_length=10) # VD: B15
    label = models.CharField("Nhãn AI/Nghiệp vụ", max_length=255, null=True, blank=True)
    value = models.TextField("Giá trị hiển thị", null=True, blank=True)
    formula = models.TextField("Công thức gốc", null=True, blank=True)
    color_code = models.CharField("Mã màu ô", max_length=20, default="FFFFFF")
    is_required = models.BooleanField("Bắt buộc nhập", default=False)
    metadata = models.JSONField("Dữ liệu máy học", default=dict, help_text="Chứa logic phụ và liên kết xuyên sheet")

    class Meta:
        verbose_name = "4. Chi tiết Ô"
        verbose_name_plural = "4. Chi tiết Ô"
        unique_together = ('sheet', 'cell_address')

    def __str__(self):
        return f"{self.cell_address}: {self.label or 'N/A'} ({self.sheet.name})"

class UncertaintyLog(models.Model):
    """
    Nhật ký tự học: Những điều AI chưa rõ từ Excel sẽ đẩy về đây để anh Vũ giải đáp.
    """
    project = models.ForeignKey(ExcelProject, on_delete=models.CASCADE, verbose_name="Dự án")
    question = models.TextField("Câu hỏi AI")
    admin_answer = models.TextField("Câu trả lời của anh Vũ", null=True, blank=True)
    is_learned = models.BooleanField("Đã nạp tri thức", default=False)
    updated_at = models.DateTimeField("Cập nhật cuối", auto_now=True)

    class Meta:
        verbose_name = "5. Nhật ký AI tự học"
        verbose_name_plural = "5. Nhật ký AI tự học"

    def __str__(self):
        status = "Đã giải quyết" if self.is_learned else "Chờ trả lời"
        return f"Câu hỏi {self.id}: {status}"

@receiver(models.signals.post_delete, sender=ExcelProject)
def auto_delete_file(sender, instance, **kwargs):
    """
    Tự động xóa file vật lý trên ổ cứng khi xóa Dự án trên Admin.
    """
    if instance.file_path and os.path.isfile(instance.file_path.path):
        os.remove(instance.file_path.path)