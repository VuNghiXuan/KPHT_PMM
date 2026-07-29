"""
Tên tệp: apps/ai_assistant/tests.py
Mô tả: Viết Unit Test cho phân hệ ai_assistant, kiểm thử FileProcessor trích xuất đa định dạng
       thông qua tệp tạm thời và kiểm tra trạng thái kết nối Redis phục vụ RAG/WebSocket.
Tác giả: Kỹ sư phần mềm cao cấp - Dự án vnxChatBot
Module liên kết: apps.ai_assistant.file_processor, apps.ai_assistant.utils
"""

import tempfile
from django.test import TestCase
from apps.ai_assistant.file_processor import FileProcessor
from apps.ai_assistant.utils import check_redis_status


class AIAssistantTestCase(TestCase):
    """
    Class: AIAssistantTestCase
    Mô tả: Kiểm thử toàn diện các tiện ích cốt lõi của phân hệ AI Assistant, 
           bao gồm xử lý tệp văn bản và trạng thái kết nối hạ tầng Redis.
    """

    def setUp(self):
        """
        Thiết lập dữ liệu ban đầu cho các test case ai_assistant.
        """
        print("\n⚙️ [SETUP]: Đang khởi tạo dữ liệu mẫu cho test case AIAssistant...")

    def test_file_processor_txt(self):
        """
        Kiểm thử nghiệp vụ: FileProcessor phải trích xuất chính xác nội dung 
        từ định dạng file văn bản thuần (TXT) thông qua đường dẫn tệp thực tế[cite: 1].
        
        Why: 
        Đảm bảo bước đầu tiên của RAG Pipeline nhận diện và đọc đúng nội dung dữ liệu 
        từ ổ đĩa trước khi chuyển hóa thành các vector nhúng (embeddings).
        """
        print("🧪 [TEST 1]: Đang kiểm tra FileProcessor với định dạng TXT...")
        
        # Tạo một file văn bản tạm thời để kiểm thử hàm đọc tệp
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as temp_file:
            temp_file.write("vnxChatBot AI-as-a-Team-Member RAG Pipeline Test.")
            temp_file_path = temp_file.name

        try:
            # Gọi phương thức xử lý tệp TXT của FileProcessor bằng đường dẫn tệp
            extracted_text = FileProcessor.process_txt(temp_file_path)
            
            self.assertIsNotNone(
                extracted_text, 
                "FileProcessor không được trả về giá trị None khi xử lý file TXT[cite: 1]."
            )
            self.assertIn(
                "vnxChatBot", 
                extracted_text, 
                "Nội dung trích xuất phải chứa từ khóa chính xác từ file[cite: 1]."
            )
            print("🎉 [TEST 1]: Trích xuất tệp TXT thành công tuyệt đối!")
        finally:
            # Dọn dẹp tệp tạm sau khi test xong
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def test_redis_status_utility(self):
        """
        Kiểm thử nghiệp vụ: Hàm kiểm tra trạng thái Redis phải trả về kết quả 
        phản hồi dạng boolean hoặc trạng thái kết nối của hệ thống[cite: 1].
        """
        print("🧪 [TEST 2]: Đang kiểm tra tiện ích kết nối Redis (check_redis_status)...")
        redis_status = check_redis_status()
        
        # Kết quả trả về của check_redis_status phải là kiểu boolean
        self.assertIsInstance(
            redis_status, 
            bool, 
            "Trạng thái Redis trả về phải là giá trị kiểu boolean[cite: 1]."
        )
        print(f"✅ [TEST 2]: Trạng thái kết nối Redis hiện tại là: {redis_status}")
        print("🎉 [TEST 2]: Kiểm thử tiện ích Redis thành công!")

# python manage.py test apps.ai_assistant.tests --verbosity=2