# apps/core/models.py
"""
Mục đích: Định nghĩa User và Profile cho vnxChatBot.
Tác giả: Kiến trúc sư vnxChatBot
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property

class User(AbstractUser):
    """
    User model tùy chỉnh cho vnxChatBot.
    Kế thừa từ AbstractUser để hỗ trợ đăng nhập mặc định.
    """
    email = models.EmailField(unique=True, verbose_name="Email đăng nhập")

    class Meta:
        verbose_name = "Người dùng"

    @cached_property
    def get_profile(self):
        try:
            return self.profile
        except:
            return None
        

class Profile(models.Model):
    """
    Mở rộng thông tin người dùng.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Ảnh đại diện")
    bio = models.TextField(max_length=500, blank=True, verbose_name="Tiểu sử")

    def __str__(self):
        return f"Profile của {self.user.username}"

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.get_or_create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, created, **kwargs):
        if hasattr(instance, 'profile'):
            instance.profile.save()