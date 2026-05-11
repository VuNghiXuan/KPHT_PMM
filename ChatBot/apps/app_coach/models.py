from django.db import models

class DataType(models.Model):
    '''
    DataType (Lò luyện Prompt): 
    Nói ngắn gọn: DataType là Thầy giáo, KnowledgeDraft là Bài tập làm văn, còn UncertaintyLog là Sổ tay giải đáp thắc mắc.
    

    Anh hãy coi đây là "Phòng đào tạo" hoặc "Cẩm nang quy chuẩn". Nó không chứa dữ liệu của bất kỳ sheet nào cụ thể, nó chỉ chứa phương pháp luận.

    Tại sao nó quan trọng: Tiệm vàng có nhiều loại nghiệp vụ (Phiếu thu chi, Bảng giá vàng, Chuyển đổi mẫu...). Mỗi loại cần một "ông thầy" AI có kiến thức khác nhau.

    Ứng dụng thực tế:

    Anh tạo một DataType tên là "Kế toán Thu Chi". Anh nạp system_prompt chuyên về định khoản.

    Anh tạo cái khác tên là "Kỹ thuật Gia công". Anh nạp Prompt chuyên về tuổi vàng, hao hụt.

    Khi nào dùng: Khi anh muốn định nghĩa "Cách mà AI nên suy nghĩ" cho một nhóm sheet có tính chất tương đồng.
    '''

    name = models.CharField("Tên loại dữ liệu", max_length=100)
    code = models.CharField("Mã (Miner code)", max_length=50, unique=True)
    is_important = models.BooleanField("Trọng tâm nghiệp vụ", default=False)
    
    # "Bộ não" của AI
    system_prompt = models.TextField(
        "System Prompt cho AI", 
        blank=True, 
        null=True, 
        help_text="Dạy AI đóng vai gì. VD: Bạn là kế toán trưởng tiệm vàng Ứng Dụng Vàng chuyên về định giá."
    )
    user_prompt_template = models.TextField(
        "User Prompt Template", 
        blank=True, 
        null=True, 
        help_text="Dùng biến {{metadata}} để AI biết chỗ dán dữ liệu Excel vào và {{sheet_name}} để lấy tên sheet."
    )
    
    # Cấu hình Model AI ưu tiên cho loại dữ liệu này
    ai_model_preference = models.CharField(
        "Ưu tiên Model",
        max_length=50,
        choices=[('GROQ', 'Groq (Nhanh/Nghiệp vụ thường)'), ('OLLAMA', 'Ollama (Bảo mật/Logic phức tạp)')],
        default='GROQ'
    )

    class Meta:
        verbose_name = "Cấu hình AI Coach"
        verbose_name_plural = "Cấu hình AI Coach"

    def __str__(self):
        return f"{self.name} ({self.code})"