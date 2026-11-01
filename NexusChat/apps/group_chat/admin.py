from django.contrib import admin
from .models import ChatGroup, Membership

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1

@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    inlines = [MembershipInline] # Cho phép thêm thành viên ngay trong trang nhóm