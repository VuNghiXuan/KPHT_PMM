"""
File: apps/core/admin.py
Mô tả: Đăng ký các model core (User, Company, Profile) vào Django Admin UI.
Tác giả: NexusChat Engineering Team
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Profile
from .models import DevDashboard
from django.shortcuts import redirect

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
    # raw_id_fields giúp tìm kiếm và chọn user/company nhanh hơn thông qua Popup
    raw_id_fields = ('user', 'company')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Tùy chỉnh giao diện quản lý User trong Admin.
    Kế thừa từ UserAdmin để đảm bảo đầy đủ chức năng quản lý tài khoản.
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    
    # fieldsets dành cho trang Sửa (Edit)
    fieldsets = UserAdmin.fieldsets
    
    # add_fieldsets là bắt buộc để trang Thêm (Add) User hiển thị form tạo tài khoản
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email',)}),
    )

@admin.register(DevDashboard)
class DevDashboardAdmin(admin.ModelAdmin):
    # Khi nhấn vào menu này, nó redirect sang trang Dashboard
    def changelist_view(self, request, extra_context=None):
        return redirect('/dev/architecture/')
    
    # Ẩn nút "Add" vì ta không cần thêm record vào đây
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False