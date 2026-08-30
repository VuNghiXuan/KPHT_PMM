# Module: document_processor.py
# Path: apps/ai_assistant/services/document_processor.py
# Description: Xử lý trích xuất văn bản từ tài liệu sử dụng Docling/Marker, phân rã khối thông minh 
#              và quản lý vòng đời tri thức (Knowledge Lifecycle) gắn chặt với group_id qua RawDocument.

import os
import logging
from django.conf import settings
from apps.ai_assistant.vector_store import VectorDBManager
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

class DocumentProcessorService:
    """
    Class: DocumentProcessorService
    Description: 
        Đóng gói toàn bộ quy trình tiền xử lý tài liệu thông minh, tích hợp sẵn 
        cơ chế trích xuất đa định dạng chuẩn mở (Marker/Docling) và phân rã khối (Chunking).
    """

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        """
        Trích xuất văn bản thuần túy từ tệp tin (.txt, .md, .csv) làm cơ chế fallback an toàn.
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ [DocumentProcessorService] Không tìm thấy đường dẫn file: {file_path}")
            return ""

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ [DocumentProcessorService Error] Lỗi đọc file {file_path}: {str(e)}")
            return ""

    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Trích xuất văn bản từ tệp tin thôngผ่าน Docling/Marker, 
        giúp chuyển đổi tài liệu phức tạp hoặc bảng biểu sang Markdown sạch.
        Có cơ chế fallback thông minh về file text thuần.
        """
        ext = os.path.splitext(file_path)[1].lower()
        extracted_text = ""

        try:
            # 1. Thử nghiệm trích xuất bằng Docling (Ưu tiên số 1 cho PDF/Document phức tạp)
            if ext == '.pdf':
                try:
                    converter = DocumentConverter()
                    result = converter.convert(file_path)
                    extracted_text = result.document.export_to_markdown()
                    logger.info("📄 [Docling] Trích xuất PDF thành công sang Markdown.")
                    return extracted_text
                except ImportError:
                    logger.warning("⚠️ Thư viện 'docling' chưa được cài đặt. Đang chuyển qua fallback.")
                except Exception as docling_err:
                    logger.warning(f"⚠️ Docling lỗi ({str(docling_err)}). Đang chuyển qua fallback.")

            # 2. Fallback về bộ phân tích file tiêu chuẩn
            return DocumentProcessorService.extract_text_from_file(file_path)

        except Exception as e:
            logger.error(f"❌ [Lỗi trích xuất file {file_path}]: {str(e)}")
            return ""

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """
        Chia nhỏ văn bản (Chunking) có chồng lấp (overlap) để giữ ngữ cảnh tốt nhất cho RAG.
        """
        if not text:
            return []
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks

    @classmethod
    def process_and_index(cls, raw_document):
        """
        Luồng Knowledge Lifecycle với RawDocument: 
        - Trích xuất file -> Lưu nội dung thô vào RawDocument (pending/staging) -> Chờ AI Auditor phân tích & quản trị viên duyệt.
        """
        if not raw_document or not raw_document.document or not raw_document.document.file:
            logger.warning("⚠️ [Knowledge Lifecycle] RawDocument không chứa file đính kèm hợp lệ.")
            return False

        file_path = raw_document.document.file.path
        raw_text = cls.extract_text(file_path)
        
        if not raw_text.strip():
            logger.warning("⚠️ [Knowledge Lifecycle] Nội dung file trống hoặc không trích xuất được text.")
            raw_document.status = 'FAILED'
            raw_document.save(update_fields=['status'])
            return False

        # Cập nhật nội dung thô để hệ thống/quản trị viên kiểm duyệt
        raw_document.raw_content = raw_text
        raw_document.status = 'STAGING'
        raw_document.save(update_fields=['raw_content', 'status'])

        logger.info(f"⏳ [Knowledge Lifecycle] RawDocument ID {raw_document.id} đang ở trạng thái 'STAGING' cho Group ID: {raw_document.group_id}")
        return True

    @staticmethod
    def commit_to_vector_db(knowledge_chapter):
        """
        Được gọi tự động qua Django Signal khi KnowledgeChapter chuyển sang trạng thái 'approved'.
        Đảm bảo cô lập tuyệt đối theo group_id.
        """
        if getattr(knowledge_chapter, 'status', 'pending') != 'approved':
            return False

        try:
            # Lấy nội dung từ chương tri thức chính thức đã được phê duyệt
            chapter_content = getattr(knowledge_chapter, 'content', '')
            if not chapter_content:
                return False

            chunks = DocumentProcessorService.chunk_text(chapter_content)
            vector_manager = VectorDBManager()
            
            # Xóa các embedding cũ trước khi thêm mới
            vector_manager.delete_unit_embeddings(unit_id=knowledge_chapter.id, group_id=knowledge_chapter.group_id)
            
            # Tạo danh sách metadata khớp 1-1 với từng chunk để tránh mất identifier
            chunks_metadatas = [
                {
                    "chapter_id": str(knowledge_chapter.id),
                    "group_id": str(knowledge_chapter.group_id),
                    "chunk_index": i
                }
                for i in range(len(chunks))
            ]

            vector_manager.add_texts(
                texts=chunks, 
                metadatas=chunks_metadatas,
                group_id=knowledge_chapter.group_id
            )

            logger.info(f"✅ [VectorDB] Đã index thành công {len(chunks)} chunks cho Chapter ID {knowledge_chapter.id} (Group ID: {knowledge_chapter.group_id})")
            return True
        except Exception as e:
            logger.error(f"❌ [VectorDB Error] Không thể đồng bộ Vector cho Chapter ID {knowledge_chapter.id}: {str(e)}")
            return False

   
    @classmethod
    def create_draft_chapters_from_raw(cls, raw_document):
        """
        Khởi tạo các KnowledgeChapter ở trạng thái 'pending' từ nội dung thô của RawDocument.
        Tuân thủ tuyệt đối quy tắc Hard Scoping theo group_id.
        """
        from apps.group_chat.models import KnowledgeChapter, KnowledgeUnit
        
        if not raw_document.raw_content:
            return []

        # 1. Tạo một KnowledgeUnit đại diện cho tài liệu upload nếu chưa có
        knowledge_unit, _ = KnowledgeUnit.objects.get_or_create(
            group_id=raw_document.group_id,
            title=f"Tài liệu: {os.path.basename(raw_document.document.file.name)}",
            defaults={"description": "Được trích xuất tự động bởi hệ thống AI P1 Background."}
        )

        # 2. Chia nhỏ văn bản thành các đoạn (chunks) để tạo thành các chương (chapters) nháp
        chunks = cls.chunk_text(raw_document.raw_content, chunk_size=1500, overlap=300)
        created_chapters = []

        for index, chunk_text in enumerate(chunks, start=1):
            # Tự động đặt tiêu đề ngắn gọn cho chương dựa trên chunk đầu tiên
            first_line = chunk_text.split('\n')[0][:50]
            chapter_title = f"Phần {index}: {first_line if first_line else 'Nội dung chi tiết'}"

            chapter = KnowledgeChapter.objects.create(
                group_id=raw_document.group_id,
                unit=knowledge_unit,
                title=chapter_title,
                summary=chunk_text[:300],  # Lưu tóm tắt ngắn
                content=chunk_text,        # Nội dung chi tiết của chương
                status='pending',          # Bắt buộc là pending (Cấm đưa thẳng vào VectorDB)
                has_conflict=False
            )
            created_chapters.append(chapter)

        logger.info(f"📚 [Knowledge Lifecycle] Đã tạo thành công {len(created_chapters)} KnowledgeChapter (pending) cho RawDoc ID {raw_document.id}")
        return created_chapters