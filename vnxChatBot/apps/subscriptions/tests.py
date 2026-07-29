"""
Tên tệp: apps/subscriptions/tests.py
Mô tả: Viết Unit Test cho phân hệ subscriptions, kiểm tra cơ chế tự động khởi tạo 
       gói cước Free khi tạo nhóm thông qua Django Signal và việc nâng cấp gói dịch vụ.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.subscriptions.models, apps.subscriptions.signals, apps.group_chat.models
"""

from django.test import TestCase
from apps.core.models import User
from apps.group_chat.models import ChatGroup
from apps.subscriptions.models import Subscription


class SubscriptionTestCase(TestCase):
    """
    Class: SubscriptionTestCase
    Mô tả: Kiểm thử toàn diện các nghiệp vụ liên quan đến gói cước 
           của nhóm làm việc (ChatGroup) trong phân hệ subscriptions.
    """

    def setUp(self):
        """
        Thiết lập dữ liệu ban đầu cho các test case.
        Tạo sẵn một User và một ChatGroup tương thích với cấu trúc Tenant Isolation.
        """
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case Subscriptions...")
        self.owner = User.objects.create_user(username='sub_test_user', password='password123')
        
        # Khởi tạo ChatGroup (signal sẽ tự động tạo Subscription đi kèm)
        self.group = ChatGroup.objects.create(name='Nhóm Kiểm Thử Subscriptions')
        print(f"🏢 [SETUP]: Đã tạo ChatGroup thành công: {self.group.name} (ID: {self.group.id})")

    def test_default_subscription_creation_signal(self):
        """
        Kiểm thử nghiệp vụ: Khi một ChatGroup mới được tạo, hệ thống phải tự động 
        kích hoạt tín hiệu (signal) để tạo một bản ghi Subscription với gói mặc định là 'free'.
        
        Why: 
        Đảm bảo mọi nhóm mới đều được gắn gói cước mặc định ngay khi khởi tạo mà không cần 
        thao tác thủ công từ phía người dùng, tuân thủ mô hình Group-Centric.
        """
        print("🧪 [TEST 1]: Đang kiểm tra cơ chế tự động tạo gói cước (Free Tier Signal)...")
        subscription = Subscription.objects.filter(group=self.group).first()
        
        self.assertIsNotNone(
            subscription, 
            "Gói cước (Subscription) phải được khởi tạo tự động khi nhóm được tạo mới."
        )
        print(f"✅ [TEST 1]: Đã tìm thấy Subscription tự động - Gói cước hiện tại: {subscription.plan_type.upper()}")

        self.assertEqual(
            subscription.plan_type, 
            'free', 
            "Gói cước mặc định cho nhóm mới phải là 'free'."
        )
        print("🎉 [TEST 1]: Kiểm tra gói cước mặc định thành công tuyệt đối!")

    def test_subscription_upgrade(self):
        """
        Kiểm thử nghiệp vụ: Nâng cấp gói cước từ 'free' lên gói cao hơn (ví dụ: 'pro') 
        và xác thực sự thay đổi trạng thái gói dịch vụ.
        """
        print("🧪 [TEST 2]: Đang kiểm tra kịch bản nâng cấp gói cước (Upgrade to Pro)...")
        subscription = self.group.subscription
        print(f"🔄 [TEST 2]: Trạng thái cũ -> Plan: {subscription.plan_type}")
        
        # Tiến hành nâng cấp gói cước lên pro
        subscription.plan_type = 'pro'
        subscription.save()

        # Tải lại dữ liệu từ database để kiểm tra tính toàn vẹn
        subscription.refresh_from_db()
        print(f"✨ [TEST 2]: Trạng thái mới -> Plan: {subscription.plan_type}")
        
        self.assertEqual(
            subscription.plan_type, 
            'pro', 
            "Gói cước phải được cập nhật thành công lên 'pro'."
        )
        print("🎉 [TEST 2]: Nâng cấp gói cước và xác thực thành công!")


# python manage.py test apps.subscriptions.tests --verbosity=2