"""
Mục đích: Xử lý trích xuất văn bản từ tài liệu và chuẩn bị dữ liệu cho Vector DB.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.vector_store, apps.ai_assistant.file_processor
"""
from apps.ai_assistant.vector_store import VectorDBManager
from apps.ai_assistant.file_processor import extract_text_from_file  # Sử dụng bộ phân tích đa định dạng chuẩn của dự án

class DocumentProcessorService:
    @staticmethod
    def extract_text(file_path):
        """
        Trích xuất văn bản từ tệp tin bất kỳ (PDF, TXT, DOCX,...) 
        thông qua FileProcessor service trung tâm.
        """
        try:
            # Gọi hàm phân tích đa định dạng chuẩn kiến trúc VnxChatBot
            return extract_text_from_file(file_path)
        except Exception as e:
            print(f"⚠️ [Lỗi trích xuất file]: {str(e)}")
            return ""

    @staticmethod
    def chunk_text(text, chunk_size=1000):
        """Chia nhỏ văn bản để tối ưu cho RAG."""
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    @classmethod
    def process_and_index(cls, knowledge_unit):
        """
        Luồng chính: Trích xuất -> Chunking -> Indexing.
        Được gọi bởi Celery Task.
        """
        if not knowledge_unit.document or not knowledge_unit.document.file:
            return False

        file_path = knowledge_unit.document.file.path
        raw_text = cls.extract_text(file_path)
        
        if not raw_text.strip():
            print("⚠️ [Cảnh báo]: Nội dung file trống hoặc không trích xuất được text.")
            return False

        chunks = cls.chunk_text(raw_text)

        # Lưu nội dung tóm tắt vào KnowledgeUnit để người dùng duyệt (Knowledge Lifecycle)
        knowledge_unit.content = raw_text[:500] + "..." 
        knowledge_unit.save()

        # Tùy chọn Auto-Index hoặc chờ phê duyệt vòng đời tri thức
        return True