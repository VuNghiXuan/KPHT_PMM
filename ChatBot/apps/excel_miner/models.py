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
        """
        Kích hoạt luồng bóc tách dữ liệu (Miner) và xây dựng tri thức (Architect).
        Đã tối ưu để tránh treo UI và đảm bảo tính toàn vẹn dữ liệu.
        """
        from django.db import transaction
        
        # 1. Cập nhật trạng thái ngay lập tức để người dùng thấy trên Dashboard
        # Sử dụng .filter().update() để tránh gọi lại hàm save() gây lặp vô tận
        ExcelProject.objects.filter(pk=self.pk).update(status='PROCESSING')
        logger.info(f"Bắt đầu bóc tách dự án: {self.name} (ID: {self.pk})")

        try:
            # Import muộn (Lazy Import) để tránh vòng lặp tham chiếu (circular import)
            from .excel_miner import ExcelMinerService
            from .letter_AI import ExcelKnowledgeArchitect

            # Sử dụng transaction.atomic để đảm bảo nếu Miner hoặc Architect lỗi thì không để lại dữ liệu rác
            with transaction.atomic():
                # BƯỚC 1: Miner - Quét toàn bộ các Sheet và ô dữ liệu
                # Bước này sẽ nạp dữ liệu vào ExcelSheet và DataField
                miner = ExcelMinerService()
                success_miner, message_miner = miner.process_project(self)
                
                if not success_miner:
                    raise Exception(f"Lỗi Miner: {message_miner}")

                # BƯỚC 2: Architect - Tổng hợp các ô thành quy trình (Business Process)
                # Dựa trên các công thức và ghi chú đã bóc tách để tạo KnowledgeDraft
                architect = ExcelKnowledgeArchitect()
                success_architect = architect.create_draft_processes_from_blueprint(self)
                
                if not success_architect:
                    # Tùy vào Architect trả về gì, ở đây giả định trả về True/False
                    raise Exception("Lỗi Architect: Không thể chuyển đổi dữ liệu thành bản thảo tri thức.")

            # 2. Hoàn tất thành công
            ExcelProject.objects.filter(pk=self.pk).update(status='COMPLETED')
            logger.info(f"Dự án {self.name} đã xử lý xong. Miner: {message_miner}")

        except Exception as e:
            # 3. Xử lý khi có lỗi: Cập nhật trạng thái và ghi log chi tiết
            ExcelProject.objects.filter(pk=self.pk).update(status='FAILED')
            
            # Ghi lại traceback đầy đủ để anh Xuân dễ debug khi code Miner bị lỗi
            import traceback
            error_msg = f"Lỗi tự động hóa tại dự án {self.name}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            # Nếu anh có trường 'error_log' trong Model, nên lưu error_msg vào đó để xem trực tiếp trên Admin
            # self.error_log = error_msg
            # self.save(update_fields=['error_log'])

    def __str__(self):
        # Hiển thị tên dự án kèm trạng thái tiếng Việt trong trang Admin
        status_map = dict([('PENDING', 'Chờ'), ('PROCESSING', 'Đang chạy'), ('COMPLETED', 'Xong'), ('FAILED', 'Lỗi')])
        display_status = status_map.get(self.status, self.status)
        return f"{self.name} [{display_status}]"

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
    

class ExcelTableRegion(models.Model):
    """Gom nhóm các ô thành từng bảng nghiệp vụ riêng biệt trong 1 sheet."""
    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='regions')
    name = models.CharField("Tên vùng bảng", max_length=255) # VD: "Chi tiết giao vàng"
    coordinates = models.CharField("Tọa độ vùng", max_length=50) # VD: "A15:M20"
    region_type = models.CharField(max_length=50, choices=[('GRID', 'Bảng dữ liệu'), ('FORM', 'Cụm nhập liệu')])
    
    def __str__(self):
        return f"{self.sheet.name} > {self.name}"

# Trong DataField, thêm liên kết này:
# region = models.ForeignKey(ExcelTableRegion, on_delete=models.SET_NULL, null=True, blank=True)