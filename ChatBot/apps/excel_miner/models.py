from django.db import models
from apps.system_monitor.models import DataType

class ExcelProject(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên dự án")
    file_path = models.FileField(upload_to='excels/', verbose_name="File gốc")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dự án Excel"
        verbose_name_plural = "Dự án Excel"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Import cục bộ để né Circular Import tuyệt đối
            from django.db import transaction
            # Đảm bảo dữ liệu đã Commit vào DB thì Miner mới có data để đọc
            transaction.on_commit(self.automate_workflow)

    def automate_workflow(self):
        """
        Luồng tự động: Miner bóc tách -> Architect soạn thảo quy trình
        """
        try:
            from .excel_miner import ExcelMinerService
            from .letter_AI import ExcelKnowledgeArchitect
            
            # 1. Đào dữ liệu thô (Dùng process_project như anh đã định nghĩa)
            miner = ExcelMinerService()
            miner.process_project(self)
            
            # 2. Tự động soạn bản thảo quy trình cho tiệm vàng
            architect = ExcelKnowledgeArchitect()
            architect.create_draft_processes_from_blueprint(self)
        except Exception as e:
            # Anh nên có logging ở đây để debug nếu AI hoặc Miner bị lỗi
            print(f"Lỗi tự động hóa dự án {self.name}: {str(e)}")
    
    def __str__(self):
        return self.name

class ExcelSheet(models.Model):
    project = models.ForeignKey(ExcelProject, on_delete=models.CASCADE, related_name='sheets')
    name = models.CharField(max_length=255, verbose_name="Tên Sheet")
    sheet_index = models.IntegerField()
    category = models.CharField(max_length=100, null=True, blank=True) 
    
    class Meta:
        verbose_name = "Sheet Excel"
        verbose_name_plural = "Danh sách Sheets"

    def __str__(self):
        return f"{self.project.name} | {self.name}"

class DataField(models.Model):
    sheet = models.ForeignKey(ExcelSheet, on_delete=models.CASCADE, related_name='fields')
    cell_address = models.CharField(max_length=10) 
    
    # Định danh nghiệp vụ
    label = models.CharField(max_length=255, null=True, blank=True) # Mã code (vd: AMOUNT)
    smart_label = models.CharField("Nhãn AI", max_length=255, null=True, blank=True) # Tên hiển thị (vd: Số tiền)
    
    # Giá trị
    value = models.TextField(null=True, blank=True)
    raw_value = models.JSONField(null=True, blank=True)
    formula = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    
    # Phân nhóm & Trạng thái
    functional_group = models.CharField(max_length=100, null=True, blank=True) # Nhóm: Khách hàng, Thanh toán...
    ui_type = models.CharField(max_length=50, default="DATA_CELL") # INPUT, BUTTON, HEADER...
    is_required = models.BooleanField(default=False) # Ô bắt buộc nhập dựa trên màu sắc
    
    # Kỹ thuật
    metadata = models.JSONField(default=dict, blank=True)
    field_type = models.ForeignKey(DataType, on_delete=models.SET_NULL, null=True)
    confidence_score = models.FloatField(default=1.0)
    is_verified = models.BooleanField(default=False)
    color_code = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        unique_together = ('sheet', 'cell_address')
        verbose_name = "Dữ liệu trong Sheets"
        verbose_name_plural = "Dữ liệu trong Sheets"
    
    def __str__(self):
        val_preview = (self.value[:20] + '..') if self.value and len(self.value) > 20 else self.value
        return f"[{self.cell_address}] {self.smart_label or self.label or 'Empty'}: {val_preview}"