"""
Mục đích: Định nghĩa KnowledgeUnit, KnowledgeTree, KnowledgeChapter và BusinessGlossary.
Giải quyết bài toán từ đa nghĩa và đồng nghĩa qua Context-Aware Entity Resolution.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.db import models
from django.utils import timezone
from .group import ChatGroup
from .document import Document, RawDocument

class BusinessGlossary(models.Model):
    """
    Từ điển nghiệp vụ theo từng nhóm: Giải quyết bài toán từ đa nghĩa và từ đồng nghĩa.
    Ví dụ: Từ '610' có thể thuộc ngữ cảnh GOLD_NEW (Vàng giao dịch) hoặc GOLD_RAW (Vàng nguyên liệu).
    """
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="glossary_terms", verbose_name="Nhóm")
    term = models.CharField(max_length=100, verbose_name="Thuật ngữ gốc", help_text="VD: 610, Vàng cha")
    context_tag = models.CharField(max_length=100, verbose_name="Nhãn ngữ cảnh", help_text="VD: GOLD_NEW, GOLD_RAW")
    synonyms = models.JSONField(default=list, verbose_name="Danh sách từ đồng nghĩa", help_text="['vàng 6 hội 1', 'hội 610']")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả ý nghĩa nghiệp vụ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Từ điển nghiệp vụ"
        verbose_name_plural = "Từ điển nghiệp vụ"
        unique_together = ('group', 'term', 'context_tag')
        indexes = [models.Index(fields=['group', 'term', 'context_tag'])]

    def __str__(self):
        return f"{self.term} [{self.context_tag}]"


class KnowledgeUnit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ duyệt'), 
        ('staging', 'Đang phân tích/Xử lý mâu thuẫn'), 
        ('approved', 'Đã duyệt'), 
        ('rollback', 'Đã hủy')
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="knowledge_units", verbose_name="Tài liệu gốc")
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="knowledge_units", verbose_name="Nhóm")
    
    # Định danh & Gắn nhãn tự động
    entity_name = models.CharField(max_length=100, verbose_name="Tên thực thể", help_text="VD: Vàng 610")
    context_tag = models.CharField(max_length=100, verbose_name="Ngữ cảnh", help_text="VD: GOLD_NEW, GOLD_RAW")
    source_reference = models.CharField(max_length=255, verbose_name="Nguồn tham chiếu")
    
    # Nội dung & Phân cấp
    content = models.TextField(verbose_name="Nội dung kiến thức")
    raw_structure_json = models.JSONField(null=True, blank=True, verbose_name="Cây mục lục gợi ý")
    
    # Đánh giá & Kiểm soát chất lượng (Giảm tải duyệt thủ công qua Confidence Score)
    confidence_score = models.FloatField(default=0.0, verbose_name="Điểm tin cậy (0.0-1.0)")
    is_conflict = models.BooleanField(default=False, verbose_name="Phát hiện mâu thuẫn")
    conflict_report = models.JSONField(null=True, blank=True, verbose_name="Chi tiết mâu thuẫn")
    
    # Vòng đời & Quản lý
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Trạng thái duyệt")
    version = models.IntegerField(default=1, verbose_name="Phiên bản")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian duyệt")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Đơn vị kiến thức"
        verbose_name_plural = "Đơn vị kiến thức"
        indexes = [
            models.Index(fields=['group', 'status', 'context_tag']),
            models.Index(fields=['entity_name']),
        ]

    def __str__(self):
        return f"{self.entity_name} ({self.context_tag}) - v{self.version} ({self.status})"

    @property
    def get_file_name(self):
        if self.document and self.document.file:
            return self.document.file.name.split('/')[-1]
        return "Không rõ tên file"

    @property
    def get_entity_name(self):
        return self.entity_name or "Chưa xác định"


class KnowledgeChapter(models.Model):
    """
    Model quản lý từng phần/chương tri thức được bóc tách từ tài liệu thô,
    hỗ trợ phân tầng cây mục lục và quy trình kiểm duyệt thủ công (Human-in-the-loop).
    """
    STATUS_CHOICES = [
        ('pending', 'Đang chờ xử lý'),
        ('staging', 'Đang phân tích / Staging'),
        ('ready_to_approve', 'Sẵn sàng phê duyệt'),
        ('conflict_detected', 'Phát hiện xung đột'),
        ('approved', 'Đã phê duyệt'),
    ]

    # 🔒 Cô lập tuyệt đối theo group_id (Hard Scoping)
    group_id = models.UUIDField(db_index=True, verbose_name="ID Nhóm chat")
    
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE, 
        related_name='children',
        verbose_name="Mục lục cha"
    )
    
    title = models.CharField(max_length=255, verbose_name="Tiêu đề chương")
    summary = models.TextField(blank=True, verbose_name="Tóm tắt nội dung chính")
    
    # 📝 Lưu trữ nội dung bản thảo do AI biên soạn khi phát hiện xung đột
    suggested_content = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Nội dung AI biên soạn gợi ý"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Trạng thái vòng đời"
    )
    
    has_conflict = models.BooleanField(default=False, verbose_name="Có mâu thuẫn ngữ nghĩa")
    
    # ⚙️ Optimistic Locking: Tránh xung đột ghi đồng thời (race conditions)
    version = models.PositiveIntegerField(default=1, verbose_name="Phiên bản khóa lạc quan")
    
    # 📊 Lưu trữ metadata, danh sách ID xung đột và lý do từ AI Auditor
    metadata = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Metadata & Thông tin xung đột"
    )
    
    created_at = models.DateTimeField(default=timezone.now, editable=False, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        indexes = [
            # 🚀 Tối ưu hóa truy vấn kết hợp group_id và trạng thái
            models.Index(fields=['group_id', 'status'], name='idx_kchapter_group_status'),
        ]
        verbose_name = "Mục lục tri thức"
        verbose_name_plural = "Mục lục tri thức"

    def __str__(self):
        return f"{self.title} - [{self.get_status_display()}] (v{self.version})"

class KnowledgeTree(models.Model):
    group = models.ForeignKey(
        ChatGroup, 
        on_delete=models.CASCADE, 
        related_name="knowledge_base",
        verbose_name="Nhóm chat"
    )
    source_doc = models.OneToOneField(
        RawDocument, 
        on_delete=models.CASCADE, 
        related_name="knowledge_node"
    )
    content_structure = models.JSONField(help_text="Cấu trúc tri thức dạng JSON.")
    confidence_score = models.FloatField(default=0.0, help_text="Điểm tin cậy từ Audit Agent")
    tags = models.JSONField(default=list, help_text="Nhãn nghiệp vụ tự động gán.")
    is_active = models.BooleanField(default=False, help_text="Chỉ True khi dữ liệu đã được Approved.")
    
    class Meta:
        verbose_name = "Cây tri thức"
        verbose_name_plural = "Cây tri thức"
        indexes = [models.Index(fields=['group', 'is_active'])]