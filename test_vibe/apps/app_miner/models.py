import os
import logging
from django.db import models, transaction
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class DataSource(models.Model):
    """
    Quản lý mọi nguồn tri thức đầu vào (Excel, Word, Ảnh toa hàng, CSV, TXT).
    Điểm khởi đầu của quy trình nạp dữ liệu cho Chatbot.
    """
    FILE_TYPES = [
        ('EXCEL', 'File Excel nghiệp vụ'),
        ('DOCX', 'Tài liệu Word (Quy định/Hợp đồng)'),
        ('TXT', 'File Text thô'),
        ('CSV', 'Bảng dữ liệu phẳng (CSV)'),
        ('IMAGE', 'Ảnh chụp (Toa hàng/Biên lai)'),
    ]

    name = models.CharField("Tên Nguồn Dữ Liệu/Dự Án", max_length=255, db_index=True)
    file_path = models.FileField("Tệp tin gốc", upload_to='knowledge_sources/%Y/%m/')
    file_type = models.CharField("Định dạng tệp", max_length=10, choices=FILE_TYPES, default='EXCEL')
    
    status = models.CharField(
        "Trạng thái xử lý", 
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
        verbose_name = "1. Nguồn Tri Thức Thô"
        verbose_name_plural = "1. Nguồn Tri Thức Thô"

    def __str__(self):
        return f"{self.name} [{self.get_file_type_display()}] -> {self.get_status_display()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Kích hoạt Miner đa năng bóc tách sau khi commit DB
            transaction.on_commit(lambda: self.automate_workflow())

    def automate_workflow(self):
        try:
            # Gọi Service mới xử lý đa định dạng file
            from .files_miner import DataMinerService
            DataMinerService.run_workflow(self)
        except Exception as e:
            logger.error(f"Lỗi khởi động Hệ thống bóc tách cho nguồn {self.name}: {str(e)}")


class DataEntry(models.Model):
    """
    Lưu tri thức tổng hợp sau bóc tách. 
    - Nếu là Excel: Đại diện cho 1 Sheet.
    - Nếu là Word/Txt/Image: Đại diện cho nội dung toàn bộ file.
    """
    project = models.ForeignKey('DataSource', on_delete=models.CASCADE, related_name='entries', verbose_name="Nguồn dữ liệu")
    name = models.CharField("Tên Phân Mục/Sheet gốc", max_length=255)
    category = models.CharField("Phân loại nghiệp vụ", max_length=100, blank=True, null=True)
    description = models.TextField("Mô tả tóm tắt (AI soạn)", blank=True, null=True)
    
    # --- PHỤC VỤ CHATBOT CHO CÁC FILE PHI-EXCEL ---
    processed_content = models.TextField("Nội dung chữ thô bóc tách (Dùng cho RAG)", blank=True, null=True)
    content_json = models.JSONField("Cấu trúc dữ liệu phẳng (JSON)", default=dict, blank=True)
    
    # --- PHỤC VỤ LOGIC EXCEL CŨ ---
    metadata = models.JSONField("Metadata Tổng Hợp Excel (Đã phân loại)", default=dict, blank=True)
    confidence_score = models.FloatField("Độ tin cậy trích xuất", default=0.0)
    
    refine_status = models.CharField(
        "Trạng thái tinh chế",
        max_length=20,
        default='PENDING',
        choices=[('PENDING', 'Chờ xử lý'), ('EXTRACTED', 'Đã vét thô'), ('REFINED', 'Đã tinh chế')]
    )

    class Meta:
        verbose_name = "2. Phân Mục Tri Thức"
        verbose_name_plural = "2. Phân Mục Tri Thức"

    def __str__(self):
        return f"{self.project.name} - {self.name} ({self.category or 'Chưa phân loại'})"


class ExcelTableRegion(models.Model):
    """ Chỉ dùng khi file_type là EXCEL để gom nhóm các bảng tính """
    sheet = models.ForeignKey(DataEntry, on_delete=models.CASCADE, related_name='regions', verbose_name="Mục tri thức")
    name = models.CharField("Tên Vùng", max_length=255)
    coordinates = models.CharField("Tọa độ (Range)", max_length=50)
    region_type = models.CharField("Loại vùng", max_length=50, default='FORM')

    class Meta:
        verbose_name = "3. Vùng Nghiệp Vụ (Excel)"
        verbose_name_plural = "3. Vùng Nghiệp Vụ (Excel)"

    def __str__(self):
        return f"{self.sheet.name} -> Vùng: {self.name}"


class DataField(models.Model):
    """ Nguyên tử dữ liệu chi tiết của từng ô. Chỉ dùng cho luồng cấu trúc phức tạp của EXCEL """
    FIELD_TYPE_CHOICES = [
        ('LOGIC', 'Công thức/Tính toán'),
        ('UI', 'Giao diện (Nút/Nhãn rác)'),
        ('DATA', 'Dữ liệu nghiệp vụ'),
        ('TRASH', 'Dữ liệu thừa/Trống'),
    ]

    sheet = models.ForeignKey(DataEntry, on_delete=models.CASCADE, related_name='fields', verbose_name="Mục tri thức")
    region = models.ForeignKey(ExcelTableRegion, on_delete=models.SET_NULL, null=True, blank=True)
    
    field_type = models.CharField("Phân loại Field", max_length=10, choices=FIELD_TYPE_CHOICES, default='DATA')
    cell_address = models.CharField("Địa chỉ ô", max_length=10)
    label = models.CharField("Nhãn nghiệp vụ", max_length=255, null=True, blank=True)
    value = models.TextField("Giá trị", null=True, blank=True)
    formula = models.TextField("Công thức", null=True, blank=True)
    
    parent_cells = models.ManyToManyField('self', symmetrical=False, related_name='child_cells', blank=True)
    metadata = models.JSONField("Dữ liệu máy học", default=dict)

    class Meta:
        verbose_name = "4. Chi tiết Ô (Excel)"
        verbose_name_plural = "4. Chi tiết Ô (Excel)"
        unique_together = ('sheet', 'cell_address')

    def __str__(self):
        return f"[{self.field_type}] {self.cell_address}: {self.label or 'N/A'}"


@receiver(models.signals.post_delete, sender=DataSource)
def auto_delete_file(sender, instance, **kwargs):
    if instance.file_path and os.path.isfile(instance.file_path.path):
        os.remove(instance.file_path.path)