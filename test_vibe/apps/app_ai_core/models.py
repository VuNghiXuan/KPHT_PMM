# app_ai_core/models.py
from django.db import models
from django.utils import timezone


def seed_default_ai_prompt(sender, **kwargs):
    """
    Hàm tự động nạp cấu hình Prompt mặc định ngay khi migrate xong, 
    chốt chặn an toàn cho hệ thống AI Miner.
    """
    # Import động ở đây để tránh lỗi gãy luồng khởi động (AppRegistryNotReady)
    from .models import AIPromptConfig

    # Kiểm tra xem hệ thống đã có cấu hình mặc định nào chưa
    if not AIPromptConfig.objects.filter(is_default=True).exists():
        default_prompt = (
            "Bạn là siêu trợ lý AI Coach - Chuyên gia phân tích nghiệp vụ (BA) hệ thống cho Kim Phát Hiệp Thành.\n"
            "Nhiệm vụ của bạn là bóc tách toàn bộ logic, luồng dữ liệu, và quy trình vận hành từ siêu dữ liệu Excel.\n\n"
            
            "⚠️ CRITICAL FOR CHATBOT RAG & BUSINESS LOGIC:\n"
            "Tuyệt đối KHÔNG ĐỂ LẠI các địa chỉ ô hoặc tọa độ Excel thuần túy (như A1, B5, Sheet2!C3) trong tài liệu kết quả.\n"
            "Dựa vào dữ liệu tiêu đề (Headers) và bối cảnh của bảng tính, bạn phải tự động DỊCH và ĐỔI TÊN các tọa độ đó thành "
            "tên thuật ngữ nghiệp vụ rõ ràng.\n"
            "Ví dụ: Thay vì viết 'Lấy A2 nhân với B5', phải viết rõ 'Lấy [Trọng lượng tổng] nhân với [Giá vàng quy tuổi]'.\n\n"
            
            "Tài liệu phải được trình bày theo đúng cấu trúc 4 phần nghiêm ngặt sau:\n\n"
            
            "## PART 1: HƯỚNG DẪN SỬ DỤNG ỨNG DỤNG (User Guide)\n"
            "\n"
            "Mô tả chi tiết các bước thao tác trên phần mềm Vàng theo thứ tự tuyến tính (Bước 1, Bước 2, Bước 3...).\n"
            "Ai là người làm? Bấm vào nút nào? Nhập dữ liệu gì vào ô nào (gọi tên nghiệp vụ)? Kết quả hiển thị ra sao?\n\n"
            
            "## PART 2: QUY TRÌNH NGHIỆP VỤ VÀ ĐIỀU KIỆN (Business Processes & Rules)\n"
            "\n"
            "Mô tả các luồng xử lý phía sau (Backend workflow) và các ràng buộc hệ thống.\n"
            "Ví dụ: Điều kiện để duyệt một hóa đơn mua vào, quy trình luân chuyển tem vàng, phân quyền giữa thu ngân và chủ tiệm.\n\n"
            
            "## PART 3: LOGIC CÔNG THỨC & TÍNH TOÁN (Calculation Logic)\n"
            "\n"
            "Liệt kê chính xác tất cả các công thức toán học/kế toán dùng trong danh mục này dưới dạng khối mã nguồn hoặc định dạng rõ ràng.\n"
            "Sử dụng hoàn toàn tên biến nghiệp vụ trong công thức (Ví dụ: Tiền công = Trọng lượng * Đơn giá công). Đính kèm chú thích tọa độ Excel cũ bên cạnh nếu cần để đối chiếu (ví dụ: '[Trọng lượng (Ô C12)]').\n"
            "Giải thích rõ ràng từng biến số trong công thức.\n\n"
            
            "## PART 4: CÂU HỎI LÀM RÕ (Nếu có)\n"
            "Nếu phát hiện điểm mâu thuẫn hoặc chưa rõ nghĩa trong dữ liệu Excel, hãy liệt kê ở đây dưới dạng: [HỎI_ANH_VŨ]: <nội dung câu hỏi>."
        )

        # Tạo bản ghi chốt chặn GLOBAL
        AIPromptConfig.objects.create(
                name="Cấu hình AI Toàn cục Mặc định",
                module_code="SYSTEM",
                function_code="GLOBAL",
                is_default=True,
                system_prompt=default_prompt,
                temperature=0.2,
                
                # 🎯 CHIẾN THUẬT CLOUD FREE: Ưu tiên bốc các con Cloud miễn phí trước
                provider_strategy="GEMINI",  # Hoặc "GROQ" tuỳ anh muốn con nào làm chốt chặn chính
                model_name="gemini-1.5-flash", # Tên model chính xác cho Cloud Gateway hứng
                
                # Ngưỡng an toàn nếu sau này anh chuyển đổi sang chế độ 'AUTO'
                max_token_threshold=20000,   # Nâng ngưỡng lên vì Gemini/Groq free cân tốt tầm 15k-20k token
                num_ctx=16384,               # Tăng context size lên cho tương xứng
                num_gpu_layers=50,
                is_active=True
            )
        print("✨ [AI_CORE] Đã nạp thành công cấu hình Prompt mặc định (Chốt chặn SYSTEM) vào cơ sở dữ liệu!")

class AIPromptConfig(models.Model):
    # 1. Định danh & Phân loại
    name = models.CharField("Tên gợi nhớ", max_length=100)
    module_code = models.CharField("Mã Module", max_length=50, db_index=True)
    function_code = models.CharField("Mã Chức năng", max_length=50, blank=True, null=True)
    is_default = models.BooleanField("Cấu hình mặc định", default=False)

    # 2. Nội dung AI
    system_prompt = models.TextField("System Prompt")
    temperature = models.FloatField("Độ sáng tạo (0.1 - 0.5)", default=0.2)

    # 3. Chiến lược LLM & Phần cứng
    PROVIDER_CHOICES = [
        ('AUTO', 'Tự động (Dựa trên Token Count)'),
        ('OLLAMA', 'Ép dùng Ollama (Local)'),
        ('GROQ', 'Ưu tiên Groq (Cloud)'),
        ('GEMINI', 'Ưu tiên Gemini (Cloud)'),
    ]
    provider_strategy = models.CharField("Chiến lược chọn AI", choices=PROVIDER_CHOICES, default='AUTO', max_length=20)
    model_name = models.CharField("Model cụ thể", max_length=100, blank=True, help_text="Ví dụ: qwen2.5:7b")
    
    # Các thông số kỹ thuật đẩy từ Gateway vào DB
    max_token_threshold = models.IntegerField("Ngưỡng chuyển đổi Token", default=6000)
    num_ctx = models.IntegerField("Context Window (Ollama)", default=8192)
    num_gpu_layers = models.IntegerField("GPU Layers (Ollama)", default=50, help_text="Số layer đẩy lên GPU, 0 là chạy CPU hoàn toàn")

    is_active = models.BooleanField("Đang kích hoạt", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cấu hình Prompt AI"
        verbose_name_plural = "Kho Prompt AI"
        unique_together = ('module_code', 'function_code')
        app_label = 'app_ai_core'

    def __str__(self):
        prefix = "[MẶC ĐỊNH] " if self.is_default else ""
        return f"{prefix}{self.module_code} | {self.function_code or 'GLOBAL'}"
    

class AITokenLog(models.Model):
    PROVIDER_CHOICES = [
        ('GEMINI', 'Google Gemini'),
        ('GROQ', 'Groq Cloud'),
    ]
    
    provider = models.CharField("Nhà cung cấp", choices=PROVIDER_CHOICES, max_length=20)
    api_key = models.CharField("API Key (Mã hóa/Ẩn)", max_length=255, unique=True)
    key_name = models.CharField("Tên gợi nhớ Key", max_length=100, help_text="Ví dụ: Key_Gemini_01")
    
    # Hạn mức cấu hình theo tài liệu Free Tier của hãng
    daily_request_limit = models.IntegerField("Hạn mức cuộc gọi/ngày", default=1500)
    daily_token_limit = models.IntegerField("Hạn mức Token/ngày", default=1000000)
    
    # Số liệu thống kê thực tế (Sẽ reset bằng Cronjob/Celery vào 00:00 mỗi ngày)
    requests_today = models.IntegerField("Số lượt gọi hôm nay", default=0)
    tokens_sent_today = models.IntegerField("Token gửi hôm nay", default=0)
    tokens_received_today = models.IntegerField("Token nhận hôm nay", default=0)
    
    # Quản trị trạng thái thông minh
    is_active = models.BooleanField("Đang hoạt động", default=True)
    last_used = models.DateTimeField("Lần cuối sử dụng", auto_now=True)
    reason_blocked = models.TextField("Lý do khóa tạm thời", blank=True, null=True)

    class Meta:
        verbose_name = "Quản trị Tài nguyên API"
        verbose_name_plural = "Rổ API Keys Cloud"
        app_label = 'app_ai_core'

    def __str__(self):
        status = "🟢 Hoạt động" if self.is_active else "🔴 KHÓA"
        return f"{self.key_name} ({self.get_provider_display()}) | Dùng: {self.requests_today} rq | {status}"

    def has_enough_quota(self, estimated_tokens=15000):
        """Kiểm tra xem Key này có đủ hạn mức an toàn để chạy đợt tiếp theo hay không"""
        if not self.is_active:
            return False
        if self.requests_today >= self.daily_request_limit:
            return False
        if (self.tokens_sent_today + estimated_tokens) >= self.daily_token_limit:
            return False
        return True