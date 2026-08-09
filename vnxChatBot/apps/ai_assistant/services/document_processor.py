# Module: document_processor.py
# Path: apps/ai_assistant/services/document_processor.py
# Description: Xử lý trích xuất văn bản từ tài liệu sử dụng Docling/Marker, phân rã khối thông minh 
#              và quản lý vòng đời tri thức (Knowledge Lifecycle) gắn chặt với group_id.
# Author: Kiến trúc sư VnxChatBot

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
        Trích xuất văn bản từ tệp tin thông qua Docling/Marker, 
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
    def process_and_index(cls, knowledge_unit):
        """
        Luồng Knowledge Lifecycle: 
        - Trích xuất file -> Tạo bản xem trước (pending) -> Chờ người dùng duyệt.
        """
        if not knowledge_unit.document or not knowledge_unit.document.file:
            logger.warning("⚠️ [Knowledge Lifecycle] KnowledgeUnit không chứa file đính kèm hợp lệ.")
            return False

        file_path = knowledge_unit.document.file.path
        raw_text = cls.extract_text(file_path)
        
        if not raw_text.strip():
            logger.warning("⚠️ [Knowledge Lifecycle] Nội dung file trống hoặc không trích xuất được text.")
            knowledge_unit.status = 'failed'
            knowledge_unit.save(update_fields=['status'])
            return False

        # Cập nhật nội dung tóm tắt để người dùng kiểm duyệt (Knowledge Lifecycle: pending state)
        knowledge_unit.content = raw_text[:1000] + "\n... [Đã trích xuất toàn bộ nội dung]"
        knowledge_unit.status = 'pending'
        knowledge_unit.save(update_fields=['content', 'status'])

        logger.info(f"⏳ [Knowledge Lifecycle] Unit ID {knowledge_unit.id} đang ở trạng thái 'pending' cho Group ID: {knowledge_unit.group_id}")
        return True

    @staticmethod
    def commit_to_vector_db(knowledge_unit):
        """
        Được gọi tự động qua Django Signal khi KnowledgeUnit chuyển từ 'pending' sang 'approved'.
        Đảm bảo cô lập tuyệt đối theo group_id[cite: 1].
        """
        if knowledge_unit.status != 'approved':
            return False

        try:
            file_path = knowledge_unit.document.file.path
            raw_text = DocumentProcessorService.extract_text(file_path)
            chunks = DocumentProcessorService.chunk_text(raw_text)

            vector_manager = VectorDBManager()
            
            # Xóa các embedding cũ và thêm mới, bắt buộc gắn group_id để cô lập dữ liệu nhóm[cite: 1]
            vector_manager.delete_unit_embeddings(unit_id=knowledge_unit.id, group_id=knowledge_unit.group_id)
            vector_manager.add_texts(
                texts=chunks, 
                metadata={"unit_id": knowledge_unit.id, "group_id": knowledge_unit.group_id},
                group_id=knowledge_unit.group_id
            )

            logger.info(f"✅ [VectorDB] Đã index thành công {len(chunks)} chunks cho Unit ID {knowledge_unit.id} (Group ID: {knowledge_unit.group_id})")
            return True
        except Exception as e:
            logger.error(f"❌ [VectorDB Error] Không thể đồng bộ Vector cho Unit ID {knowledge_unit.id}: {str(e)}")
            return False