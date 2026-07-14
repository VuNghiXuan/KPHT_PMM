"""
File: apps/group_chat/models.py
Mục đích: Quản lý cấu trúc nhóm chat và phân quyền thành viên.
Liên kết: apps.core.models.User.
"""
from django.db import models
from django.conf import settings



class ChatGroup(models.Model):
    """
    Class đại diện cho một nhóm chat riêng biệt.
    Vai trò: Lưu trữ thông tin nhóm và chủ sở hữu nhóm.
    """
    name = models.CharField(max_length=255, verbose_name="Tên nhóm")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="owned_groups",
        verbose_name="Chủ nhóm"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        through='Membership',
        related_name="chat_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nhóm chat"
        verbose_name_plural = "Các nhóm chat"

class Membership(models.Model):
    """
    Class quản lý quyền của thành viên trong nhóm.
    Kế thừa: models.Model.
    Vai trò: Định nghĩa vai trò (Chủ nhóm/Thành viên) và quyền hạn trong nhóm.
    """
    ROLE_CHOICES = (
        ('admin', 'Chủ nhóm'),
        ('member', 'Thành viên'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Tin nhắn"