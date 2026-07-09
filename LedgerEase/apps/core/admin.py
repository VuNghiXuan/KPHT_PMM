from django.contrib import admin
from .models import Company, Profile

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Cấu hình hiển thị Công ty trong Admin.
    """
    list_display = ('name', 'tax_code', 'is_active', 'created_at')
    search_fields = ('name', 'tax_code')
    list_filter = ('is_active',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Cấu hình hiển thị Profile trong Admin.
    """
    list_display = ('user', 'company')
    list_filter = ('company',)