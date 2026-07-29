"""
Tên tệp: apps/group_chat/test_group_chat.py
Mô tả: Viết Unit Test cho phân hệ group_chat, kiểm tra nghiệp vụ tạo nhóm, 
       tự động gán thành viên AI, quản lý KnowledgeUnit gắn với Document và vòng đời tri thức.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.group_chat.models, apps.group_chat.signals, apps.core.models
"""

from django.test import TestCase
from apps.core.models import User
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit


class GroupChatTestCase(TestCase):
    """
    Class: GroupChatTestCase
    Mô tả: Kiểm thử toàn diện các nghiệp vụ cốt lõi của Group-Centric trong phân hệ group_chat.
    """

    def setUp(self):
        """
        Thiết lập dữ liệu mẫu cho các test case group_chat.
        Tạo một User chủ sở hữu và một ChatGroup để kiểm tra tín hiệu (signal) tự động thêm AI member.
        """
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case GroupChat...")
        self.user = User.objects.create_user(username='group_owner', password='password123')
        self.group = ChatGroup.objects.create(name='Phòng Ban Kỹ Thuật VnxChatBot')
        print(f"🏢 [SETUP]: Đã tạo ChatGroup thành công: {self.group.name} (ID: {self.group.id})")

    def test_ai_member_auto_assignment_signal(self):
        """
        Kiểm thử nghiệp vụ: Khi một ChatGroup mới được khởi tạo, hệ thống phải tự động 
        kích hoạt tín hiệu để gán một thành viên AI (với cờ is_ai=True) vào nhóm.
        
        Why: 
        Đảm bảo đúng triết lý 'AI-as-a-Team-Member' của dự án, AI luôn hiện diện trong mọi 
        nhóm làm việc để lắng nghe thảo luận và hỗ trợ RAG mà không cần tạo User ảo thủ công.
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
        (chờ phê duyệt) và kiểm tra khả năng chuyển đổi trạng thái sang 'approved'.
        """
        print("🧪 [TEST 2]: Đang kiểm tra vòng đời tri thức (Knowledge Lifecycle - Pending to Approved)...")
        
        # Tạo bản ghi Document bắt buộc để thỏa mãn ràng buộc khóa ngoại NOT NULL của KnowledgeUnit
        self.document = Document.objects.create(
            group=self.group,
            file="groups/test_doc.txt",
            uploaded_by=self.user
        )
        
        ku = KnowledgeUnit.objects.create(
            group=self.group,
            document=self.document,
            content="Thông số kỹ thuật mẫu cho RAG Pipeline vnxChatBot.",
            status="pending"
        )
        self.assertEqual(ku.status, 'pending', "Trạng thái khởi tạo của KnowledgeUnit phải là 'pending'.")
        
        # Phê duyệt tri thức
        ku.status = 'approved'
        ku.save()
        ku.refresh_from_db()
        
        self.assertEqual(
            ku.status, 
            'approved', 
            "KnowledgeUnit phải được chuyển sang trạng thái 'approved' thành công sau khi duyệt."
        )
        print("🎉 [TEST 2]: Kiểm thử vòng đời tri thức KnowledgeUnit thành công!")

# python manage.py test apps.group_chat.test_group_chat --verbosity=2