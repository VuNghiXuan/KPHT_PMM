import os
import logging
from django.db import models, transaction
from django.dispatch import receiver
from apps.system_monitor.models import DataType

logger = logging.getLogger(__name__)

class ExcelProject(models.Model):
    """Quản lý dự án Excel: Đầu vào cho hệ thống bóc tách tri thức."""
    name = models.CharField(max_length=255, verbose_name="Tên dự án", db_index=True)
    file_path = models.FileField(
        upload_to='excels/%Y/%m/', 
        verbose_name="File gốc", 
        help_text="Hệ thống hỗ trợ .xlsx, .xls, .xlsm"
    )
    description = models.TextField("Mô tả dự án", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        "Trạng thái xử lý", 
        max_length=20, 
        choices=[('PENDING', 'Chờ xử lý'), ('PROCESSING', 'Đang bóc tách'), ('COMPLETED', 'Hoàn tất'), ('FAILED', 'Lỗi')],
        default='PENDING'
    )

    class Meta:
        verbose_name = "Dự án Excel"
        verbose_name_plural = "Dự án Excel"
        ordering = ['-uploaded_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Sử dụng on_commit để đảm bảo file đã ghi vào đĩa và DB đã lưu xong
            transaction.on_commit(lambda: self.automate_workflow())

    def automate_workflow(self):
        """Kích hoạt luồng Miner & Architect."""
        try:
            # Cập nhật trạng thái để UI hiển thị cho anh biết
            ExcelProject.objects.filter(pk=self.pk).update(status='PROCESSING')
            
            from .excel_miner import ExcelMinerService
            from .letter_AI import ExcelKnowledgeArchitect
            
            # 1. Miner bóc tách cấu trúc ô
            miner = ExcelMinerService()
            miner.process_project(self)
            
            # 2. Architect soạn thảo nội dung (Quy trình, Thuật ngữ tiệm vàng)
            architect = ExcelKnowledgeArchitect()
            architect.create_draft_processes_from_blueprint(self)
            
            ExcelProject.objects.filter(pk=self.pk).update(status='COMPLETED')
            logger.info(f"Dự án {self.name} đã được xử lý tự động thành công.")
            
        except Exception as e:
            ExcelProject.objects.filter(pk=self.pk).update(status='FAILED')
            logger.error(f"Lỗi tự động hóa dự án {self.name}: {str(e)}", exc_info=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

# --- Signal dọn dẹp file khi xóa Project ---
@receiver(models.signals.post_delete, sender=ExcelProject)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file_path and os.path.isfile(instance.file_path.path):
        os.remove(instance.file_path.path)


class ExcelSheet(models.Model):
    """Phân loại sheet để AI biết sheet nào là Bảng giá, sheet nào là Giao dịch."""
    project = models.ForeignKey(ExcelProject, on_delete=models.CASCADE, related_name='sheets')
    name = models.CharField(max_length=255, verbose_name="Tên Sheet")
    sheet_index = models.IntegerField()
    category = models.CharField(
        "Loại nghiệp vụ", 
        max_length=100, 
        null=True, blank=True,
        help_text="VD: GOLD_PRICE, EXCHANGE_LOGIC, INVENTORY"
    ) 
    
    class Meta:
        verbose_name = "Sheet Excel"
        verbose_name_plural = "Danh sách Sheets"
        unique_together = ('project', 'sheet_index')

    def __str__(self):
        return f"{self.project.name} ⮕ {self.name}"


class DataField(models.Model):
    """Lưu trữ từng đơn vị tri thức bóc tách được từ ô Excel."""
    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='fields')
    cell_address = models.CharField(max_length=10, db_index=True) 
    
    # Định danh (Giữ nguyên logic của anh nhưng tối ưu index)
    label = models.CharField("Mã định danh", max_length=255, null=True, blank=True, db_index=True)
    smart_label = models.CharField("Nhãn AI", max_length=255, null=True, blank=True)
    
    # Dữ liệu cốt lõi
    value = models.TextField("Giá trị hiển thị", null=True, blank=True)
    raw_value = models.JSONField("Dữ liệu thô", null=True, blank=True)
    formula = models.TextField("Công thức (Excel)", null=True, blank=True)
    
    # Đặc thù tiệm vàng: Bóc tách logic chuyển đổi
    # VD: "Vàng 999 -> Vàng 980: Bù khách 60.000đ"
    logic_interpretation = models.TextField("Giải thích logic ô", null=True, blank=True)
    
    # Phân nhóm & Trạng thái UI
    functional_group = models.CharField("Nhóm nghiệp vụ", max_length=100, null=True, blank=True, db_index=True)
    ui_type = models.CharField(
        "Loại thành phần", 
        max_length=50, 
        default="DATA_CELL",
        choices=[('INPUT', 'Ô nhập liệu'), ('OUTPUT', 'Ô kết quả/Tổng'), ('HEADER', 'Tiêu đề'), ('BUTTON', 'Nút bấm giả lập')]
    )
    is_required = models.BooleanField("Bắt buộc", default=False)
    
    # Kỹ thuật & Độ tin cậy
    field_type = models.ForeignKey(DataType, on_delete=models.SET_NULL, null=True)
    color_code = models.CharField("Mã màu ô", max_length=20, null=True, blank=True)
    confidence_score = models.FloatField("Độ tin cậy AI (%)", default=1.0)
    is_verified = models.BooleanField("Đã xác minh", default=False)
    metadata = models.JSONField("Thông tin kỹ thuật khác", default=dict, blank=True)

    class Meta:
        unique_together = ('sheet', 'cell_address')
        verbose_name = "Dữ liệu ô"
        verbose_name_plural = "Dữ liệu ô"
        indexes = [
            models.Index(fields=['sheet', 'label']),
            models.Index(fields=['functional_group', 'is_verified']),
        ]
    
    def __str__(self):
        prefix = f"[{self.cell_address}]"
        name = self.smart_label or self.label or 'Unnamed'
        return f"{prefix} {name}: {str(self.value)[:30]}"