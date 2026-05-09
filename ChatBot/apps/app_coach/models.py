from django.db import models

class DataType(models.Model):
    name = models.CharField("Tên loại dữ liệu", max_length=100)
    code = models.CharField("Mã (Miner code)", max_length=50, unique=True) # VD: WEIGHT, AMOUNT
    is_important = models.BooleanField("Trọng tâm nghiệp vụ", default=False)
    
    class Meta:
        verbose_name = "1. Loại dữ liệu cấu hình"
        verbose_name_plural = "1. Loại dữ liệu cấu hình"

    def __str__(self):
        return f"{self.name} ({self.code})"