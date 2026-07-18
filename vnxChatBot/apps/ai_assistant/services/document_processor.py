"""
Mục đích: Xử lý trích xuất văn bản từ tài liệu và chuẩn bị dữ liệu cho Vector DB.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.vector_store
"""
import PyPDF2 # Cần cài đặt: pip install PyPDF2
from apps.ai_assistant.vector_store import VectorDBManager

class DocumentProcessorService:
    @staticmethod
    def extract_text(file_path):
        """Trích xuất text đơn giản từ PDF. Có thể mở rộng sang Docx/Txt."""
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

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
        file_path = knowledge_unit.document.file.path
        raw_text = cls.extract_text(file_path)
        chunks = cls.chunk_text(raw_text)

        # Lưu nội dung đã trích xuất vào KnowledgeUnit để người dùng duyệt
        knowledge_unit.content = raw_text[:500] + "..." # Lưu đoạn tóm tắt
        knowledge_unit.save()

        # Ở đây, nếu bạn muốn Auto-Index ngay (không cần duyệt):
        # for chunk in chunks:
        #     VectorDBManager.upsert(
        #         group_id=knowledge_unit.group.id,
        #         text=chunk,
        #         unit_id=knowledge_unit.id
        #     )
        
        return True