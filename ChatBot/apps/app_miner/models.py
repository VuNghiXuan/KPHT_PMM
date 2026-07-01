import os, logging
from django.db import models, transaction
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class ExcelProject(models.Model):
    """
    Quản lý file Excel tổng. Điểm khởi đầu của quy trình.
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
        return f"{self.name} [{self.get_status_display()}]"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Kích hoạt Miner bóc tách sau khi commit DB
            transaction.on_commit(lambda: self.automate_workflow())

    def automate_workflow(self):
        try:
            from .excel_miner import ExcelMinerService
            ExcelMinerService.run_workflow(self)
        except Exception as e:
            logger.error(f"Lỗi khởi động Orchestrator cho dự án {self.name}: {str(e)}")

class ExcelSheet(models.Model):
    """
    Lưu thông tin từng Sheet. Gom tri thức tổng hợp tại đây.
    """
    project = models.ForeignKey('ExcelProject', on_delete=models.CASCADE, related_name='sheets', verbose_name="Dự án")
    name = models.CharField("Tên Sheet gốc", max_length=255)
    category = models.CharField("Phân loại nghiệp vụ", max_length=100, blank=True, null=True)
    description = models.TextField("Mô tả nghiệp vụ AI soạn", blank=True, null=True)
    
    # Cấu trúc JSON mới để gom: { "logic": [], "ui": [], "data": [], "trash": [] }
    metadata = models.JSONField("Metadata Tổng Hợp (Đã phân loại)", default=dict, blank=True)
    
    confidence_score = models.FloatField("Độ tin cậy (Cosine)", default=0.0)
    
    # Theo dõi tiến độ tinh chế của từng sheet
    refine_status = models.CharField(
        "Trạng thái tinh chế",
        max_length=20,
        default='PENDING',
        choices=[('PENDING', 'Chờ AI'), ('EXTRACTED', 'Đã vét thô'), ('REFINED', 'Đã tinh chế')]
    )

    class Meta:
        verbose_name = "2. Danh mục Sheet"
        verbose_name_plural = "2. Danh mục Sheet"

    def __str__(self):
        return f"Sheet: {self.name} ({self.category or 'Chưa phân loại'})"

class ExcelTableRegion(models.Model):
    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='regions', verbose_name="Sheet")
    name = models.CharField("Tên Vùng", max_length=255)
    coordinates = models.CharField("Tọa độ (Range)", max_length=50)
    region_type = models.CharField("Loại vùng", max_length=50, default='FORM')

    class Meta:
        verbose_name = "3. Vùng Nghiệp Vụ"
        verbose_name_plural = "3. Vùng Nghiệp Vụ"

class DataField(models.Model):
    """
    Nguyên tử tri thức. Đã được phân loại thô để giảm nhiễu.
    """
    FIELD_TYPE_CHOICES = [
        ('LOGIC', 'Công thức/Tính toán'),
        ('UI', 'Giao diện (Nút/Nhãn rác)'),
        ('DATA', 'Dữ liệu nghiệp vụ'),
        ('TRASH', 'Dữ liệu thừa/Trống'),
    ]

    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='fields', verbose_name="Sheet")
    region = models.ForeignKey(ExcelTableRegion, on_delete=models.SET_NULL, null=True, blank=True)
    
    field_type = models.CharField("Phân loại Field", max_length=10, choices=FIELD_TYPE_CHOICES, default='DATA')
    
    cell_address = models.CharField("Địa chỉ ô", max_length=10)
    label = models.CharField("Nhãn nghiệp vụ", max_length=255, null=True, blank=True)
    value = models.TextField("Giá trị", null=True, blank=True)
    formula = models.TextField("Công thức", null=True, blank=True)
    
    # Dùng cho AI vẽ Graph logic
    parent_cells = models.ManyToManyField('self', symmetrical=False, related_name='child_cells', blank=True)
    
    metadata = models.JSONField("Dữ liệu máy học", default=dict)

    class Meta:
        verbose_name = "4. Chi tiết Ô"
        verbose_name_plural = "4. Chi tiết Ô"
        unique_together = ('sheet', 'cell_address')

    def __str__(self):
        return f"[{self.field_type}] {self.cell_address}: {self.label or 'N/A'}"

@receiver(models.signals.post_delete, sender=ExcelProject)
def auto_delete_file(sender, instance, **kwargs):
    if instance.file_path and os.path.isfile(instance.file_path.path):
        os.remove(instance.file_path.path)