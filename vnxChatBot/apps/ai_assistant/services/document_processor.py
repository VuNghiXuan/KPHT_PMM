# Module: document_processor.py
# Path: apps/ai_assistant/services/document_processor.py
# Description: Xử lý trích xuất văn bản từ tài liệu sử dụng Docling/Marker, 
#              phân rã khối thông minh dựa trên Token Budget & Semantic Chunking,
#              và quản lý vòng đời tri thức (Knowledge Lifecycle) gắn chặt với group_id qua RawDocument.

import os
import re
import logging
from django.conf import settings
from apps.ai_assistant.vector_store import VectorDBManager
from apps.ai_assistant.models.text_choices import KnowledgeStatus
# Import Module xử lý text độc lập vừa tạo 🚀
from apps.ai_assistant.services.text_cleaner import TextCleanerService

logger = logging.getLogger(__name__)

# Thử nghiệm import tiktoken cho việc tính chính xác số lượng Token
try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    TOKENIZER = None
    logger.warning("⚠️ Thư viện 'tiktoken' chưa được cài đặt. Hệ thống sẽ fallback về ước tính char/token.")


class DocumentProcessorService:
    """
    Class: DocumentProcessorService
    Description: 
        Đóng gói toàn bộ quy trình tiền xử lý tài liệu thông minh, tích hợp sẵn 
        cơ chế trích xuất đa định dạng chuẩn mở (Marker/Docling), Semantic Chunking theo ngữ nghĩa,
        và quản lý Token Budget nhằm tránh chạm trần Rate Limit / Context Window của LLM API.
    """

    @staticmethod
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        if TOKENIZER:
            return len(TOKENIZER.encode(text))
        return len(text) // 4

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
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
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.pdf':
                try:
                    from docling.document_converter import DocumentConverter
                    converter = DocumentConverter()
                    result = converter.convert(file_path)
                    extracted_text = result.document.export_to_markdown()
                    logger.info("📄 [Docling] Trích xuất PDF thành công sang Markdown.")
                    
                    # ✅ Tự động sửa lỗi đứt khoảng trắng OCR ngay sau khi trích xuất
                    return TextCleanerService.fix_ocr_spacing(extracted_text)
                except ImportError:
                    logger.warning("⚠️ Thư viện 'docling' chưa được cài đặt. Đang chuyển qua fallback.")
                except Exception as docling_err:
                    logger.warning(f"⚠️ Docling lỗi ({str(docling_err)}). Đang chuyển qua fallback.")

            raw_text = DocumentProcessorService.extract_text_from_file(file_path)
            return TextCleanerService.fix_ocr_spacing(raw_text)

        except Exception as e:
            logger.error(f"❌ [Lỗi trích xuất file {file_path}]: {str(e)}")
            return ""

    @classmethod
    def semantic_split_boundaries(cls, text: str) -> list[str]:
        if not text.strip():
            return []

        raw_sections = re.split(r'(\n{2,}|(?=^#{1,6}\s))', text, flags=re.MULTILINE)
        units = []

        for section in raw_sections:
            section_str = section.strip()
            if not section_str:
                continue
            
            if cls.count_tokens(section_str) > 600:
                sentences = re.split(r'(?<=[.?!])\s+', section_str)
                units.extend([s.strip() for s in sentences if s.strip()])
            else:
                units.append(section_str)

        return units

    @classmethod
    def chunk_by_token_budget(
        cls, 
        text: str, 
        target_tokens: int = 500, 
        max_tokens: int = 800, 
        overlap_tokens: int = 100
    ) -> list[str]:
        semantic_units = cls.semantic_split_boundaries(text)
        if not semantic_units:
            return []

        chunks = []
        current_chunk_units = []
        current_tokens = 0

        for unit in semantic_units:
            unit_tokens = cls.count_tokens(unit)

            if unit_tokens > max_tokens:
                if current_chunk_units:
                    chunks.append("\n\n".join(current_chunk_units))
                    current_chunk_units = []
                    current_tokens = 0
                
                chars_per_token = max(1, len(unit) // unit_tokens)
                chunk_char_size = max_tokens * chars_per_token
                overlap_char_size = overlap_tokens * chars_per_token
                
                for i in range(0, len(unit), chunk_char_size - overlap_char_size):
                    sub_chunk = unit[i:i + chunk_char_size]
                    chunks.append(sub_chunk)
                continue

            if current_tokens + unit_tokens > max_tokens:
                chunks.append("\n\n".join(current_chunk_units))
                
                if current_chunk_units:
                    last_unit = current_chunk_units[-1]
                    if cls.count_tokens(last_unit) <= overlap_tokens:
                        current_chunk_units = [last_unit, unit]
                        current_tokens = cls.count_tokens(last_unit) + unit_tokens
                    else:
                        current_chunk_units = [unit]
                        current_tokens = unit_tokens
                else:
                    current_chunk_units = [unit]
                    current_tokens = unit_tokens
            else:
                current_chunk_units.append(unit)
                current_tokens += unit_tokens

            if current_tokens >= target_tokens:
                chunks.append("\n\n".join(current_chunk_units))
                last_unit = current_chunk_units[-1]
                if cls.count_tokens(last_unit) <= overlap_tokens:
                    current_chunk_units = [last_unit]
                    current_tokens = cls.count_tokens(last_unit)
                else:
                    current_chunk_units = []
                    current_tokens = 0

        if current_chunk_units:
            remaining_text = "\n\n".join(current_chunk_units)
            if not chunks or remaining_text != chunks[-1]:
                chunks.append(remaining_text)

        logger.info(f"✂️ [Semantic Chunking] Đã phân rã văn bản ({cls.count_tokens(text)} tokens) thành {len(chunks)} chunks an toàn.")
        return chunks

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        target_tokens = chunk_size // 4
        max_tokens = int(target_tokens * 1.3)
        overlap_tokens = overlap // 4

        return cls.chunk_by_token_budget(
            text=text,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens
        )

    @classmethod
    def process_and_index(cls, raw_document):
        if not raw_document or not hasattr(raw_document, 'document') or not raw_document.document or not raw_document.document.file:
            logger.warning("⚠️ [Knowledge Lifecycle] RawDocument không chứa file đính kèm hợp lệ.")
            return False

        file_path = raw_document.document.file.path
        raw_text = cls.extract_text(file_path)
        
        if not raw_text.strip():
            logger.warning("⚠️ [Knowledge Lifecycle] Nội dung file trống hoặc không trích xuất được text.")
            raw_document.status = 'FAILED'
            raw_document.save(update_fields=['status'])
            return False

        raw_document.raw_content = raw_text
        raw_document.status = 'STAGING'
        raw_document.save(update_fields=['raw_content', 'status'])

        logger.info(f"⏳ [Knowledge Lifecycle] RawDocument ID {raw_document.id} đang ở trạng thái 'STAGING' cho Group ID: {raw_document.group_id}")
        return True

    @staticmethod
    def commit_to_vector_db(knowledge_chapter):
        current_status = getattr(knowledge_chapter, 'status', None)
        if current_status not in [KnowledgeStatus.APPROVED, 'approved', 'APPROVED']:
            logger.warning(f"⛔ [VectorDB] Từ chối commit: Chapter ID {getattr(knowledge_chapter, 'id', None)} chưa ở trạng thái 'approved'.")
            return False

        try:
            chapter_content = getattr(knowledge_chapter, 'content', '')
            if not chapter_content:
                return False

            chunks = DocumentProcessorService.chunk_by_token_budget(
                text=chapter_content,
                target_tokens=300,
                max_tokens=500,
                overlap_tokens=50
            )
            
            vector_manager = VectorDBManager()
            vector_manager.delete_unit_embeddings(unit_id=knowledge_chapter.id, group_id=knowledge_chapter.group_id)
            
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

            logger.info(f"✅ [VectorDB] Đã index thành công {len(chunks)} semantic chunks cho Chapter ID {knowledge_chapter.id} (Group ID: {knowledge_chapter.group_id})")
            return True
        except Exception as e:
            logger.error(f"❌ [VectorDB Error] Không thể đồng bộ Vector cho Chapter ID {knowledge_chapter.id}: {str(e)}")
            return False

    @classmethod
    def commit_chapter_to_vector_db(cls, knowledge_chapter):
        return cls.commit_to_vector_db(knowledge_chapter)

    @classmethod
    def create_draft_chapters_from_raw(cls, raw_document):
        """
        Khởi tạo các KnowledgeChapter ở trạng thái 'pending' từ nội dung thô của RawDocument.
        Đã tích hợp TextCleanerService để lọc tiêu đề thông minh (Hybrid Layer 1 + 2) và sửa lỗi OCR.
        """
        from apps.group_chat.models import KnowledgeChapter
        
        if not raw_document.raw_content:
            return []

        # 1. Chunking dữ liệu thô
        chunks = cls.chunk_by_token_budget(
            text=raw_document.raw_content,
            target_tokens=400,
            max_tokens=650,
            overlap_tokens=60
        )
        created_chapters = []

        for index, chunk_text in enumerate(chunks, start=1):
            # 🚀 Gọi TextCleanerService sinh tiêu đề chuẩn sạch (loại bỏ ##, sửa lỗi OCR, né công thức/bảng)
            chapter_title = TextCleanerService.generate_chunk_title(chunk_text, index)

            chapter = KnowledgeChapter.objects.create(
                group_id=raw_document.group_id,
                title=chapter_title,              # ✅ Tiêu đề chuẩn sạch
                summary=chunk_text[:300],         # ✅ Tóm tắt ngắn
                suggested_content=chunk_text,     # ✅ Nội dung chi tiết
                status='pending', 
                has_conflict=False
            )
            created_chapters.append(chapter)

        logger.info(f"📚 [Knowledge Lifecycle] Đã tạo thành công {len(created_chapters)} KnowledgeChapter (pending) cho RawDoc ID {raw_document.id}")
        return created_chapters