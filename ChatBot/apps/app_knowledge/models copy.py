from django.db import models

# --- NHÓM 1: ĐỊNH NGHĨA NGHIỆP VỤ (HỆ ĐIỀU HÀNH) ---
class BusinessTask(models.Model):
    TASK_CHOICES = [
        ('EXTRACT', 'Bóc tách dữ liệu (Excel/PDF/Img)'),
        ('LOGIC_GEN', 'Soạn thảo quy trình vận hành'),
        ('CHAT_GUIDE', 'Định hướng hội thoại Chatbot'),
    ]

    name = models.CharField("Tên nghiệp vụ", max_length=255)
    slug = models.SlugField("Mã định danh (Slug)", unique=True, help_text="Dùng để khớp với file JSON và Router")
    task_type = models.CharField("Loại nhiệm vụ", max_length=50, choices=TASK_CHOICES, default='EXTRACT')
    
    # Gom AIPromptTemplate vào đây để quản lý tập trung
    system_prompt = models.TextField("System Instruction", help_text="Vai trò và luật chơi của AI")
    user_prompt_template = models.TextField("User Prompt Template", help_text="Dùng {{data}} hoặc {{context}} để truyền nội dung")
    
    # Học tăng cường (Reinforcement Learning)
    learning_notes = models.TextField("Ghi chú tri thức (AI tự đúc kết)", blank=True, null=True)
    
    is_active = models.BooleanField("Đang hoạt động", default=True)
    priority = models.IntegerField("Độ ưu tiên", default=0)

    class Meta:
        verbose_name = "Nghiệp vụ điều hướng"
        ordering = ['-priority', 'name']

    def __str__(self):
        return f"{self.name} [{self.slug}]"


# --- NHÓM 2: XỬ LÝ & ĐỐI SOÁT (DYNAMICS) ---
class KnowledgeDraft(models.Model):
    task = models.ForeignKey(BusinessTask, on_delete=models.CASCADE, related_name='drafts')
    # Kết nối với Project bên app_miner
    project_id = models.IntegerField("ID dự án gốc") 
    content = models.TextField("Nội dung AI soạn thảo")
    
    status = models.CharField("Trạng thái", max_length=20, choices=[
        ('PENDING', 'Chờ duyệt'),
        ('CONFLICT', 'Phát hiện mâu thuẫn'),
        ('APPROVED', 'Đã thống nhất'),
    ], default='PENDING')
    
    conflict_details = models.TextField("Chi tiết mâu thuẫn", blank=True, null=True, help_text="AI tự liệt kê các điểm khác biệt so với tri thức cũ")
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bản thảo tri thức"


# --- NHÓM 3: KHO TRI THỨC SẠCH (DÀNH CHO CHATBOT) ---
class BusinessTerm(models.Model):
    term = models.CharField("Thuật ngữ", max_length=255, unique=True)
    definition = models.TextField("Định nghĩa nghiệp vụ")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Từ điển nghiệp vụ"

class BusinessProcess(models.Model):
    task = models.ForeignKey(BusinessTask, on_delete=models.SET_NULL, null=True)
    name = models.CharField("Tên quy trình/công thức", max_length=255)
    description = models.TextField("Mô tả chi tiết")
    logic_rules = models.JSONField("Công thức máy tính (JSON)", null=True, blank=True)
    is_published = models.BooleanField("Cho phép Chatbot sử dụng", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quy trình chính thức"


# --- NHÓM 4: VÒNG LẶP HỌC TẬP (REINFORCEMENT LEARNING) ---
class CorrectionLedger(models.Model):
    """Lưu vết sửa lỗi để cập nhật ngược lại learning_notes của BusinessTask"""
    task = models.ForeignKey(BusinessTask, on_delete=models.CASCADE)
    draft = models.ForeignKey(KnowledgeDraft, on_delete=models.CASCADE)
    original_value = models.TextField("AI bóc tách sai")
    corrected_value = models.TextField("Chủ tiệm sửa lại đúng")
    reason = models.CharField("Lý do thay đổi", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nhật ký sửa lỗi (Học tăng cường)"