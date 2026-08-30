"""
Mục đích: Định nghĩa thực thể Nhóm chat và Thành viên nhóm theo chuẩn Group-Centric.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class ChatGroup(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên nhóm")
    plan_type = models.CharField(max_length=50, default="free", verbose_name="Gói dịch vụ")
    max_members = models.IntegerField(default=6, verbose_name="Số thành viên tối đa")
    is_active = models.BooleanField(default=True, verbose_name="Nhóm đang hoạt động")
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả nhóm")
    is_admin_group = models.BooleanField(default=False, verbose_name="Là nhóm Admin hệ thống?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Nhóm chat"
        verbose_name_plural = "Danh sách nhóm chat"

    def __str__(self):
        return f"{self.name} ({self.plan_type})"

    @property
    def ai_provider(self):
        config = getattr(self, 'ai_config', None)
        return config.provider if config else 'gemini'

    @ai_provider.setter
    def ai_provider(self, value):
        from apps.ai_assistant.models import GroupAIProvider
        config, created = GroupAIProvider.objects.get_or_create(group=self)
        config.provider = value
        config.save()

    @property
    def ai_model(self):
        config = getattr(self, 'ai_config', None)
        return config.model_name if config else 'gemini-2.0-flash'

    @ai_model.setter
    def ai_model(self, value):
        from apps.ai_assistant.models import GroupAIProvider
        config, created = GroupAIProvider.objects.get_or_create(group=self)
        config.model_name = value
        config.save()

    @property
    def custom_api_key(self):
        config = getattr(self, 'ai_config', None)
        return config.api_key if config else ''

    @custom_api_key.setter
    def custom_api_key(self, value):
        from apps.ai_assistant.models import GroupAIProvider
        config, created = GroupAIProvider.objects.get_or_create(group=self)
        config.api_key = value
        config.save()

    @property
    def pending_knowledge_count(self):
        return self.knowledge_units.filter(status='PENDING').count()

    @property
    def approved_knowledge_count(self):
        return self.knowledge_units.filter(status='APPROVED').count()


class Membership(models.Model):
    ROLE_CHOICES = [('admin', 'Admin'), ('member', 'Member')]
    
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="memberships", verbose_name="Nhóm")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="memberships", verbose_name="Người dùng")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name="Vai trò")
    is_ai = models.BooleanField(default=False, verbose_name="Là AI?", help_text="Đánh dấu nếu đây là thành viên AI")

    class Meta:
        verbose_name = "Thành viên nhóm"
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.username if self.user else 'AI'} - {self.group.name}"


class GroupMember(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('owner', 'Owner'), ('member', 'Member')], default='member')
    can_approve_internal = models.BooleanField(default=False)
    can_approve_public = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.role == 'owner':
            self.can_approve_internal = True
            self.can_approve_public = True
        super().save(*args, **kwargs)