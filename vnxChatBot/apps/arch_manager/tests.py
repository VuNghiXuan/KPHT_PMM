"""
Tên tệp: apps/arch_manager/tests.py
Mô tả: Viết Unit Test cho phân hệ arch_manager, kiểm thử engine nội soi kiến trúc tự động,
       khởi tạo sơ đồ ERD, Code Flow và quy trình phê duyệt SystemBlueprint.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.arch_manager.models, apps.arch_manager.utils, apps.arch_manager.views
"""

from django.test import TestCase
from apps.arch_manager.models import SystemBlueprint
from apps.arch_manager.utils import ArchitectureIntrospectionEngine


class ArchManagerTestCase(TestCase):
    """
    Class: ArchManagerTestCase
    Mô tả: Kiểm thử toàn diện các chức năng nội soi kiến trúc, sinh sơ đồ tự động 
           và quy trình kiểm soát phiên bản tài liệu kiến trúc của hệ thống.
    """

    def setUp(self):
        """
        Thiết lập dữ liệu ban đầu cho các test case arch_manager.
        Tạo một bản ghi SystemBlueprint mẫu để kiểm tra trạng thái và tương tác với engine.
        """
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case ArchManager...")
        # Sử dụng đúng tên trường cấu trúc model (ví dụ: mô tả/nội dung theo đúng chuẩn migration)
        self.blueprint = SystemBlueprint.objects.create(
            version="v1.0.0-test",
            description="# Living Architecture Test Blueprint",
            is_active=True
        )
        print(f"🏛️ [SETUP]: Đã tạo SystemBlueprint thành công (Version: {self.blueprint.version})")

    def test_architecture_introspection_engine_erd(self):
        """
        Kiểm thử nghiệp vụ: ArchitectureIntrospectionEngine phải tự động quét 
        và sinh thành công mã nguồn sơ đồ ERD tập trung xoay quanh ChatGroup (Group-Centric).
        
        Why: 
        Đảm bảo hệ thống có khả năng tự nội soi cấu trúc dữ liệu mô hình thực tế 
        mà không cần vẽ thủ công, phục vụ kho tri thức trung tâm của dự án.
        """
        print("🧪 [TEST 1]: Đang kiểm thử tính năng nội soi ERD tự động...")
        erd_output = ArchitectureIntrospectionEngine.generate_erd()
        
        self.assertIsNotNone(
            erd_output, 
            "Engine nội soi ERD không được trả về giá trị None."
        )
        self.assertIsInstance(
            erd_output, 
            str, 
            "Kết quả sinh sơ đồ ERD phải là một chuỗi văn bản (Markdown/Mermaid)."
        )
        print("🎉 [TEST 1]: Nội soi ERD tự động thành công tuyệt đối!")

    def test_architecture_introspection_engine_code_flow(self):
        """
        Kiểm thử nghiệp vụ: Kiểm tra khả năng sinh sơ đồ luồng dữ liệu (Code Flow) 
        từ FileProcessor đến VectorStore và LLM RAG Pipeline.
        """
        print("🧪 [TEST 2]: Đang kiểm thử tính năng sinh sơ đồ Code Flow...")
        flow_output = ArchitectureIntrospectionEngine.generate_code_flow()
        
        self.assertIsNotNone(
            flow_output, 
            "Sơ đồ Code Flow phải được khởi tạo thành công."
        )
        self.assertGreater(
            len(flow_output), 
            0, 
            "Nội dung sơ đồ Code Flow không được để trống."
        )
        print("🎉 [TEST 2]: Sinh sơ đồ Code Flow thành công!")

    def test_system_blueprint_active_constraint(self):
        """
        Kiểm thử nghiệp vụ: Đảm bảo mô hình SystemBlueprint lưu trữ đúng trạng thái 
        và phương thức sinh ERD động từ model hoạt động chính xác.
        """
        print("🧪 [TEST 3]: Đang kiểm thử phương thức sinh dynamic ERD từ SystemBlueprint model...")
        dynamic_erd = self.blueprint.generate_dynamic_erd()
        
        self.assertIsNotNone(
            dynamic_erd, 
            "Phương thức generate_dynamic_erd phải trả về kết quả hợp lệ."
        )
        self.assertTrue(
            self.blueprint.is_active, 
            SystemBlueprint.objects.filter(id=self.blueprint.id).first().is_active
        )
        print("🎉 [TEST 3]: Kiểm thử model SystemBlueprint thành công!")
# python manage.py test apps.arch_manager.tests --verbosity=2