"""
File: apps/core/admin.py
Mục đích: Cấu hình giao diện quản trị Django Admin cho User tùy chỉnh và Profile.
Tác giả: Kiến trúc sư vnxChatBot
Module liên kết: apps.core.models
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile

class ProfileInline(admin.StackedInline):
    """
    Inline hiển thị thông tin Profile ngay trong trang chi tiết của User.
    """
    model = Profile
    can_delete = False
    verbose_name_plural = 'Thông tin chi tiết Profile'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Quản lý User tùy chỉnh trên Django Admin, tích hợp sẵn Profile dạng Inline.
    """
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')