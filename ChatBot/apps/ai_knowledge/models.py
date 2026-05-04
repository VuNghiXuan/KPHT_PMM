from django.db import models

# --- NHÓM 1: TRI THỨC HỆ THỐNG (CORE KNOWLEDGE) ---

class BusinessTerm(models.Model):
    """Từ điển nghiệp vụ chuẩn hóa."""
    term = models.CharField("Thuật ngữ", max_length=255, unique=True)
    definition = models.TextField("Định nghĩa nghiệp vụ")
    context = models.TextField("Ngữ cảnh sử dụng", null=True, blank=True)
    is_common = models.BooleanField("Thuật ngữ phổ biến", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Thuật ngữ chính thức"
        verbose_name_plural = "1. Từ điển nghiệp vụ (Đã duyệt)"

    def __str__(self):
        return self.term

class BusinessProcess(models.Model):
    """Quy trình & Công thức vận hành chính thức."""
    name = models.CharField("Tên quy trình", max_length=255)
    description = models.TextField("Mô tả quy trình (Markdown)", null=True, blank=True)
    steps = models.JSONField("Danh sách bước (JSON)", null=True, blank=True)
    logic_rules = models.TextField("Công thức / Logic tổng quát", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Quy trình nghiệp vụ"
        verbose_name_plural = "2. Quản lý quy trình (Chính thức)"

    def __str__(self):
        return self.name

class SystemGuide(BusinessProcess): 
    """Proxy model để hiển thị hướng dẫn vận hành riêng trên Admin."""
    class Meta:
        proxy = True
        verbose_name = "📖 HƯỚNG DẪN VẬN HÀNH"
        verbose_name_plural = "📖 HƯỚNG DẪN VẬN HÀNH"

# --- NHÓM 2: CỬA NGÕ TIẾP NHẬN & DRAFT (DYNAMICS) ---

class KnowledgeDraft(models.Model):
    """
    Bản kiến thức AI nháp.
    Dùng trường 'category' để phân loại thay vì tạo nhiều bảng.
    """
    CATEGORY_CHOICES = [('PROCESS', 'Quy trình'), ('TERM', 'Thuật ngữ'), ('LOGIC', 'Quy tắc Logic')]
    STATUS_CHOICES = [('PENDING', 'Chờ xử lý'), ('AI_PROCESSED', 'AI đã viết'), ('APPROVED', 'Đã duyệt nạp')]

    project = models.ForeignKey('excel_miner.ExcelProject', on_delete=models.CASCADE, related_name='drafts')
    category = models.CharField("Loại bản thảo", max_length=20, choices=CATEGORY_CHOICES, default='PROCESS')
    
    title = models.CharField("Tiêu đề/Thuật ngữ", max_length=255)
    content = models.TextField("Nội dung (Markdown/JSON)")
    
    # Lưu vết metadata (Sheet gốc, ô dữ liệu...)
    origin_metadata = models.JSONField("Nguồn gốc dữ liệu", null=True, blank=True)
    
    status = models.CharField("Trạng thái", max_length=20, default='PENDING', choices=STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bản thảo tri thức"
        verbose_name_plural = "3. Sàng lọc & Soạn thảo (Draft Area)"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

class BusinessLogicRule(models.Model):
    """Quy tắc Logic bóc tách - Kết nối trực tiếp với bản thảo hợp nhất."""
    draft = models.ForeignKey(KnowledgeDraft, on_delete=models.CASCADE, related_name='logic_rules', null=True, 
        blank=True)
    rule_name = models.CharField("Tên công thức", max_length=255)
    formula = models.TextField("Công thức (Python Style)")
    variables = models.JSONField("Biến số", help_text="Ví dụ: ['weight', 'purity']")
    explanation = models.TextField("Giải thích", null=True, blank=True)

    class Meta:
        verbose_name = "Quy tắc Logic"
        verbose_name_plural = "4. Quy tắc Logic bóc tách"

# --- NHÓM 3: CẤU HÌNH AI (AI CONFIG) ---

class AIPromptTemplate(models.Model):
    TASK_CHOICES = [
        ('USER_GUIDE', 'Viết hướng dẫn sử dụng'),
        ('GEN_CODE', 'Viết Code Logic'),
        ('UI_SCRIPT', 'Kịch bản giao diện'),
    ]
    name = models.CharField("Tên nhiệm vụ", max_length=255)
    task_type = models.CharField("Loại nhiệm vụ", max_length=50, choices=TASK_CHOICES)
    system_prompt = models.TextField("System Prompt")
    template_content = models.TextField("Template (Dùng {{context}})")
    
    class Meta:
        verbose_name = "Mẫu Prompt AI"
        verbose_name_plural = "5. Cấu hình Prompt AI"

    def __str__(self):
        return self.name