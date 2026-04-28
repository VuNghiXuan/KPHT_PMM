from django.db import models
from apps.excel_miner.models import DataField

class BusinessTerm(models.Model):
    term = models.CharField(max_length=255, unique=True, verbose_name="Thuật ngữ/Khái niệm")
    definition = models.TextField(verbose_name="Định nghĩa nghiệp vụ")
    context = models.TextField(null=True, blank=True, verbose_name="Ngữ cảnh sử dụng")
    # Liên kết với ô Excel cụ thể để khi cần AI có thể tra lại dữ liệu gốc
    source_field = models.ForeignKey(DataField, on_delete=models.SET_NULL, null=True, blank=True)
    is_common = models.BooleanField(default=True, verbose_name="Thuật ngữ phổ biến")

    class Meta:
        verbose_name = "Thuật ngữ"
        verbose_name_plural = "Từ điển nghiệp vụ"

    def __str__(self):
        return self.term

class BusinessProcess(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên quy trình")
    # Dùng TextField thay vì JSONField để anh viết mô tả quy trình dạng Markdown cho dễ
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả tổng quan")
    steps = models.JSONField(verbose_name="Các bước thực hiện", help_text="Lưu dưới dạng danh sách các bước")
    logic_rules = models.TextField(verbose_name="Quy tắc logic (Công thức)")
    
    class Meta:
        verbose_name = "Quy trình"
        verbose_name_plural = "Quy trình nghiệp vụ"

    def __str__(self):
        return self.name

class IntentRouter(models.Model):
    intent_name = models.CharField(max_length=100, unique=True, verbose_name="Mã ý định")
    display_name = models.CharField(max_length=255, null=True, verbose_name="Tên ý định (Dễ hiểu)")
    # AI sẽ dựa vào đây để xác định xem câu hỏi thuộc về nghiệp vụ nào
    keywords = models.TextField(verbose_name="Từ khóa nhận diện", help_text="Phân cách bằng dấu phẩy")
    target_app = models.CharField(max_length=50, verbose_name="App xử lý")
    hit_count = models.IntegerField(default=0, verbose_name="Số lần sử dụng")

    class Meta:
        verbose_name = "Định tuyến ý định"
        verbose_name_plural = "Bộ định tuyến ý định (Router)"

    def __str__(self):
        return self.display_name or self.intent_name