"""
Mục đích: Khởi tạo dữ liệu mẫu cho môi trường Local Development.
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model  # Sử dụng get_user_model
from apps.group_chat.models import ChatGroup, Membership

# Lấy model User hiện tại của hệ thống (core.User)
User = get_user_model()

class Command(BaseCommand):
    help = 'Khởi tạo nhóm và thành viên AI mẫu'

    def handle(self, *args, **options):
        # 1. Tạo một User admin để test
        user, created = User.objects.get_or_create(username='admin_test')
        if created:
            user.set_password('123456')
            user.save()
            self.stdout.write(self.style.SUCCESS('Đã tạo user admin_test'))

        # 2. Tạo nhóm mẫu
        group, g_created = ChatGroup.objects.get_or_create(name="Hiệp Thành Jewelry")
        
        # 3. Thêm thành viên
        membership, m_created = Membership.objects.get_or_create(
            group=group,
            user=user,
            defaults={'role': 'admin', 'is_ai': False}
        )
        
        self.stdout.write(self.style.SUCCESS(f'Đã khởi tạo xong nhóm: {group.name}'))