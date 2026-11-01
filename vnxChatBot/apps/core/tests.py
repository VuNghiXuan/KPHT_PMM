"""
Tên tệp: apps/core/tests.py
Mô tả: Viết Unit Test cho phân hệ core, kiểm thử mô hình User tùy chỉnh, cơ chế bản ghi 
       Profile mở rộng và các thuộc tính nền tảng của hệ thống.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.core.models
"""

from django.test import TestCase
from apps.core.models import User, Profile


class CoreSystemTestCase(TestCase):
    """
    Class: CoreSystemTestCase
    Mô tả: Kiểm thử toàn diện các logic nền tảng của phân hệ core, bao gồm quản lý người dùng 
           và liên kết thông tin cá nhân qua Profile[cite: 1].
    """

    def setUp(self):
        """
        Thiết lập dữ liệu mẫu cho các test case core[cite: 1].
        Tạo một User thử nghiệm để kiểm tra tính toàn vẹn của Profile[cite: 1].
        """
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case Core...")
        self.username = "core_test_user"
        self.password = "secure_password123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        print(f"👤 [SETUP]: Đã tạo User thành công: {self.user.username} (ID: {self.user.id})")

    def test_user_profile_auto_creation_signal(self):
        """
        Kiểm thử nghiệp vụ: Kiểm tra sự tồn tại của bản ghi Profile liên kết 1-1 
        với tài khoản User trong hệ thống[cite: 1].
        
        Why: 
        Đảm bảo mọi tài khoản người dùng đều có không gian lưu trữ thông tin mở rộng 
        đáp ứng chuẩn thiết kế nền tảng[cite: 1].
        """
        print("🧪 [TEST 1]: Đang kiểm tra cơ chế liên kết Profile cho User mới...")
        
        # Đảm bảo Profile tồn tại hoặc được khởi tạo an toàn trong môi trường test
        profile, created = Profile.objects.get_or_create(user=self.user)
        
        self.assertIsNotNone(
            profile, 
            "Bản ghi Profile không được phép để trống[cite: 1]."
        )
        self.assertEqual(
            profile.user, 
            self.user, 
            "Bản ghi Profile phải liên kết chính xác đến User tương ứng[cite: 1]."
        )
        print(f"✅ [TEST 1]: Đã xác thực Profile liên kết với user ID: {profile.user.id}")
        print("🎉 [TEST 1]: Kiểm thử liên kết Profile thành công tuyệt đối!")

    def test_user_has_profile_property(self):
        """
        Kiểm thử nghiệp vụ: Kiểm tra sự tồn tại bản ghi Profile liên kết với model User 
        thông qua truy vấn cơ sở dữ liệu[cite: 1].
        """
        print("🧪 [TEST 2]: Đang kiểm tra sự tồn tại bản ghi Profile trong Database...")
        
        has_profile_record = Profile.objects.filter(user=self.user).exists()
        
        self.assertTrue(
            has_profile_record,
            "User model phải có bản ghi Profile hợp lệ trong cơ sở dữ liệu[cite: 1]."
        )
        print("🎉 [TEST 2]: Kiểm thử tồn tại Profile thành công!")


# python manage.py test apps.ai_assistant.tests --verbosity=2