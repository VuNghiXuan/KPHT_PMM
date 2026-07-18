"""
Mục đích: Quản lý gói cước và giới hạn thành viên cho từng ChatGroup.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models (ChatGroup)
"""
from django.db import models
from apps.group_chat.models import ChatGroup

class Subscription(models.Model):
    """
    Quản lý trạng thái và giới hạn của nhóm.
    Tại sao (Why): Phân tách tài nguyên theo nhóm (Group-Centric), 
    đảm bảo mỗi nhóm là một thực thể độc lập.
    """
    PLAN_CHOICES = [
        ('free', 'Free'), 
        ('pro', 'Pro'), 
        ('enterprise', 'Enterprise')
    ]
    
    group = models.OneToOneField(
        ChatGroup, 
        on_delete=models.CASCADE, 
        related_name="subscription",
        verbose_name="Nhóm chat"
    )
    plan_type = models.CharField(
        max_length=20, 
        choices=PLAN_CHOICES, 
        default='free',
        verbose_name="Loại gói dịch vụ"
    )
    member_limit = models.IntegerField(
        default=6, 
        verbose_name="Giới hạn thành viên",
        help_text="Tổng số thành viên tối đa (bao gồm AI)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")

    class Meta:
        verbose_name = "Đăng ký dịch vụ nhóm"
        verbose_name_plural = "Đăng ký dịch vụ nhóm"

    def __str__(self):
        return f"{self.group.name} - {self.get_plan_type_display()}"