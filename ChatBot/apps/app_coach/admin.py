from django.contrib import admin
from .models import DataType

@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_important')
    search_fields = ('name', 'code')
    list_filter = ('is_important',)

# Tạm thời comment hoặc xóa các dòng đăng ký Admin cho ProjectStructure, IntentManagement... 
# vì các Model này anh em mình đã lược bỏ để đưa vào metadata của DataField cho gọn.