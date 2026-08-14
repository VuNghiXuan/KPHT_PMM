"""
Tên tệp: apps/group_chat/test_group_chat.py
Mô tả: Viết Unit Test cho phân hệ group_chat, kiểm tra nghiệp vụ tạo nhóm, 
       tự động gán thành viên AI, quản lý KnowledgeUnit gắn với Document và vòng đời tri thức.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.group_chat.models, apps.group_chat.signals, apps.core.models, apps.ai_assistant.models
"""

from django.test import TestCase
from apps.core.models import User
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit
from apps.ai_assistant.models import GroupAIProvider

class GroupChatTestCase(TestCase):
    """
    Class: GroupChatTestCase[cite: 1]
    Mô tả: Kiểm thử toàn diện các nghiệp vụ cốt lõi của Group-Centric trong phân hệ group_chat.
    """

    def setUp(self):
        """Thiết lập dữ liệu mẫu cho các test case group_chat[cite: 1]."""
        self.user = User.objects.create_user(username='group_test_user', password='password123')
        
        # 1. Khởi tạo ChatGroup theo chuẩn Modular Monolith (không gán trực tiếp thuộc tính cũ)[cite: 1]
        self.group = ChatGroup.objects.create(name='Phòng Ban Kỹ Thuật VnxChatBot')
        
        # 2. Khởi tạo cấu hình AI qua bảng liên kết chuẩn của ai_assistant[cite: 1]
        GroupAIProvider.objects.get_or_create(
            group=self.group,
            defaults={'provider': 'gemini', 'model_name': 'gemini-1.5-flash'}
        )
        
        self.membership = Membership.objects.create(
            user=self.user,
            group=self.group,
            role='admin'
        )
        
        self.document = Document.objects.create(
            group=self.group,
            file='test_doc.txt',
            uploaded_by=self.user
        )
        
        self.knowledge_unit = KnowledgeUnit.objects.create(
            group=self.group,
            document=self.document,
            entity_name='Vàng 610',
            context_tag='Giao dịch',
            source_reference='test_doc.txt',
            content='Test knowledge unit content',
            status='pending'
        )

    def test_ai_member_auto_assignment_signal(self):
        """
        Kiểm thử nghiệp vụ: Khi một ChatGroup mới được khởi tạo, hệ thống phải tự động 
        kích hoạt tín hiệu để gán một thành viên AI (với cờ is_ai=True) vào nhóm[cite: 1].
        """
        print("🧪 [TEST 1]: Đang kiểm tra cơ chế tự động gán AI member (AI-as-a-Team-Member)...")
        
        ai_membership = Membership.objects.filter(group=self.group, is_ai=True).first()
        
        self.assertIsNotNone(
            ai_membership, 
            "Mỗi ChatGroup mới phải tự động có ít nhất một thành viên AI được gán thông qua Signal."
        )
        print(f"✅ [TEST 1]: Đã tìm thấy thành viên AI trong nhóm: {ai_membership.group.name}")
        print("🎉 [TEST 1]: Kiểm thử gán AI member tự động thành công tuyệt đối!")

    def test_knowledge_unit_lifecycle_state(self):
        """
        Kiểm thử nghiệp vụ: Khởi tạo một Document và KnowledgeUnit với trạng thái ban đầu là 'pending' 
        (chờ phê duyệt) và kiểm tra khả năng chuyển đổi trạng thái sang 'approved'[cite: 1].
        """
        print("🧪 [TEST 2]: Đang kiểm tra vòng đời tri thức (Knowledge Lifecycle - Pending to Approved)...")
        
        ku = self.knowledge_unit
        
        self.assertEqual(ku.status, 'pending', "Trạng thái khởi tạo của KnowledgeUnit phải là 'pending'.")
        
        # Giả lập thao tác phê duyệt tri thức (Human-in-the-loop)
        ku.status = 'approved'
        ku.save()
        ku.refresh_from_db()
        
        self.assertEqual(
            ku.status, 
            'approved', 
            "KnowledgeUnit phải được chuyển sang trạng thái 'approved' thành công sau khi duyệt."
        )
        print("🎉 [TEST 2]: Kiểm thử vòng đời tri thức KnowledgeUnit thành công!")