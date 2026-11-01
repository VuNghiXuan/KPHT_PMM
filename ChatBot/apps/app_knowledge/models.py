import hashlib
import logging
from django.db import models

logger = logging.getLogger(__name__)

class KnowledgeDraft(models.Model):
    """
    Sản phẩm dở dang: Lưu trữ HDSD chờ anh Vũ duyệt.
    """
    # Liên kết app_miner (Phải dùng apps.app_miner nếu đã đổi folder)
    project = models.ForeignKey(
        'app_miner.ExcelProject', # Cập nhật tên app label mới nếu cần
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='drafts'
    )
    
    sheet = models.OneToOneField(
        'app_miner.ExcelSheet', 
        on_delete=models.CASCADE, 
        related_name='knowledge_draft', 
        null=True
    )
    
    # QUAN TRỌNG: Đổi hướng sang app_ai_core để quản lý Prompt tập trung
    # Nếu anh vẫn dùng DataType của app_coach thì giữ nguyên, 
    # nhưng thường thì anh nên link tới AIPromptConfig hoặc dùng Code định danh.
    data_type = models.ForeignKey(
        'app_coach.DataType', 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    
    term = models.CharField("Thuật ngữ/Logic", max_length=255)
    category = models.CharField(
        "Phân loại", 
        max_length=50, 
        choices=[('LOGIC', 'Logic tính toán'), ('TERM', 'Định nghĩa/Nghiệp vụ')],
        default='TERM'
    )
    
    content = models.TextField("Mô tả chi tiết cho AI") 
    
    status = models.CharField(
        "Trạng thái", 
        max_length=20, 
        default='PENDING',
        choices=[
            ('PENDING', 'Chờ AI tóm tắt'),
            ('AI_READY', 'AI đã soạn xong'),
            ('EDITED', 'Anh Vũ đã sửa'),
            ('FINAL', 'Đã chốt (Nạp vào RAG)')
        ]
    )
    
    origin_metadata = models.JSONField("Metadata gốc từ Miner", default=dict, blank=True)
    backup_hash = models.CharField(max_length=64, unique=True, editable=False, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "1. Bản thảo tri thức"
        verbose_name_plural = "1. Bản thảo tri thức"

    def __str__(self):
        return f"Draft: {self.term} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # 1. Tạo Hash định danh dựa trên Project và Sheet để không bị trùng
        if self.project and self.sheet:
            hash_src = f"{self.project.id}_{self.sheet.id}" # Dùng ID cho chắc chắn
            self.backup_hash = hashlib.sha256(hash_src.encode()).hexdigest()

        # 2. AUTO-SYNC: Cập nhật mô tả vào ExcelSheet để đồng bộ hệ thống Miner
        if self.sheet and self.content:
            try:
                # Đảm bảo đường dẫn import đúng với cấu trúc folder apps/
                from apps.app_miner.models import ExcelSheet 
                ExcelSheet.objects.filter(id=self.sheet.id).update(description=self.content)
            except ImportError:
                logger.error("Không thể import ExcelSheet để đồng bộ.")

        super().save(*args, **kwargs)

class LearningLog(models.Model):
    """
    Sổ tay lỗi nghiệp vụ: Nơi AI hỏi bài và anh Vũ trả lời.
    """
    project = models.ForeignKey(
        'app_miner.ExcelProject', 
        on_delete=models.CASCADE,
        verbose_name="Dự án"
    )
    question = models.TextField("Câu hỏi AI")
    admin_answer = models.TextField("Câu trả lời của anh Vũ", null=True, blank=True)
    is_learned = models.BooleanField("Đã nạp tri thức", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "2. Nhật ký AI tự học"
        verbose_name_plural = "2. Nhật ký AI tự học"

    def __str__(self):
        return f"Hỏi bài: {self.question[:50]}..."