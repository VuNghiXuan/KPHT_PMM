from django.db import models

# --- NHÓM 1: TRI THỨC CHÍNH THỨC (Dùng để Chatbot trả lời) ---

class BusinessTerm(models.Model):
    """Từ điển nghiệp vụ đã chuẩn hóa 100%."""
    term = models.CharField("Thuật ngữ", max_length=255, unique=True)
    definition = models.TextField("Định nghĩa nghiệp vụ")
    context = models.TextField("Ngữ cảnh sử dụng", null=True, blank=True)
    source_field = models.ForeignKey(
        'excel_miner.DataField', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
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

# --- NHÓM 2: CỬA NGÕ TIẾP NHẬN (DRAFT AREA) ---

class BusinessProcessDraft(models.Model):
    """Nơi AI soạn thảo quy trình từ Blueprint để anh 'gọt giũa'."""
    project = models.ForeignKey('excel_miner.ExcelProject', on_delete=models.CASCADE)
    sheet_name = models.CharField("Thuộc Sheet", max_length=255)
    process_name = models.CharField("Tên quy trình dự kiến", max_length=255)
    draft_content = models.TextField("Nội dung bản thảo (Markdown)")
    logic_mapping = models.JSONField("Bản đồ ngữ cảnh UI", null=True, blank=True)
    status = models.CharField("Trạng thái", max_length=20, default='PENDING', choices=[
        ('PENDING', 'Chờ gởi AI'),
        ('REVISED', 'Đã chỉnh sửa'),
        ('APPROVED', 'Đã duyệt nạp')
    ])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bản thảo quy trình"
        verbose_name_plural = "3. Soạn thảo quy trình (Draft)"
        unique_together = ('project', 'sheet_name') # Tránh tạo trùng bản thảo cho cùng 1 sheet

    def __str__(self):
        return f"{self.sheet_name} - {self.process_name}"

class BusinessTermDraft(models.Model):
    """Nơi lưu thuật ngữ thô từ Excel hoặc từ AI bóc tách ra."""
    project = models.ForeignKey('excel_miner.ExcelProject', on_delete=models.CASCADE)
    process_draft = models.ForeignKey(
        BusinessProcessDraft, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='related_terms'
    )
    term = models.CharField("Thuật ngữ thô", max_length=500)
    sheet_name = models.CharField("Tên Sheet gốc", max_length=255)
    context = models.TextField("Vị trí/Ngữ cảnh trong Excel", null=True, blank=True)
    ui_type = models.CharField("Phân loại UI", max_length=100, null=True, blank=True)
    definition = models.TextField("AI Dự đoán định nghĩa", null=True, blank=True)
    suggested_code = models.CharField("Mã Code", max_length=100, null=True, blank=True)
    status = models.CharField("Trạng thái", max_length=20, default='PENDING', choices=[
        ('PENDING', 'Chờ duyệt'),
        ('SENT', 'Đang đợi AI'),
        ('DONE', 'Đã duyệt')
    ])

    class Meta:
        verbose_name = "Bản nháp thuật ngữ"
        verbose_name_plural = "4. Sàng lọc thuật ngữ (Draft)"
        unique_together = ('project', 'term', 'sheet_name')

    def __str__(self):
        return self.term

# --- NHÓM 3: BỘ NÃO ĐIỀU HƯỚNG & LOGIC ---

class IntentRouter(models.Model):
    """Điều hướng câu hỏi khách hàng đến đúng module xử lý."""
    intent_name = models.CharField("Mã ý định", max_length=100, unique=True)
    display_name = models.CharField("Tên ý định", max_length=255, null=True)
    keywords = models.TextField("Từ khóa nhận diện (Phân cách bằng dấu phẩy)")
    target_app = models.CharField("App xử lý", max_length=50)
    hit_count = models.IntegerField("Số lượt hỏi", default=0)

    class Meta:
        verbose_name = "Định tuyến AI"
        verbose_name_plural = "5. Bộ định tuyến AI (Router)"

class BusinessLogicRule(models.Model):
    """Lưu trữ các công thức tính toán bóc tách từ quy trình."""
    process_draft = models.ForeignKey(
        BusinessProcessDraft, 
        on_delete=models.CASCADE, 
        related_name='logic_rules_draft'
    )
    rule_name = models.CharField("Tên công thức", max_length=255)
    formula = models.TextField("Công thức (Excel/Python style)")
    variables = models.JSONField("Các biến số cần nạp", help_text="Ví dụ: ['weight', 'purity']")
    explanation = models.TextField("Giải thích bình dân", null=True, blank=True)

    class Meta:
        verbose_name = "Quy tắc Logic"
        verbose_name_plural = "6. Quy tắc Logic (Bóc tách từ AI)"

    def __str__(self):
        return self.rule_name