# Module: document_processor.py
# Path: apps/ai_assistant/services/document_processor.py
# Description: Xử lý trích xuất văn bản từ tài liệu sử dụng Docling/Marker, 
#               phân rã khối thông minh dựa trên Token Budget & Semantic Chunking,
#               và quản lý vòng đời tri thức (Knowledge Lifecycle) gắn chặt với group_id qua RawDocument.

import os
import re
import logging
from django.conf import settings
from apps.ai_assistant.vector_store import VectorDBManager
from apps.ai_assistant.models.text_choices import KnowledgeStatus

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
        """
        Đếm chính xác số lượng Token của văn bản bằng tiktoken.
        Nếu không có tiktoken, fallback về công thức ước tính: 1 token ≈ 4 ký tự.
        """
        if not text:
            return 0
        if TOKENIZER:
            return len(TOKENIZER.encode(text))
        return len(text) // 4

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

        try:
            if ext == '.pdf':
                try:
                    from docling.document_converter import DocumentConverter
                    converter = DocumentConverter()
                    result = converter.convert(file_path)
                    extracted_text = result.document.export_to_markdown()
                    logger.info("📄 [Docling] Trích xuất PDF thành công sang Markdown.")
                    return extracted_text
                except ImportError:
                    logger.warning("⚠️ Thư viện 'docling' chưa được cài đặt. Đang chuyển qua fallback.")
                except Exception as docling_err:
                    logger.warning(f"⚠️ Docling lỗi ({str(docling_err)}). Đang chuyển qua fallback.")

            return DocumentProcessorService.extract_text_from_file(file_path)

        except Exception as e:
            logger.error(f"❌ [Lỗi trích xuất file {file_path}]: {str(e)}")
            return ""

    @classmethod
    def semantic_split_boundaries(cls, text: str) -> list[str]:
        """
        Chia nhỏ văn bản thành các đoạn nguyên vẹn theo thứ tự ưu tiên ngữ nghĩa:
        1. Tiêu đề Markdown (# Header) & Đoạn văn kép (\n\n)
        2. Xuống dòng đơn (\n)
        3. Dấu kết thúc câu (. , ? , ! )
        """
        if not text.strip():
            return []

        # Tách theo tiêu đề Markdown hoặc khoảng trống hai hàng (\n\n)
        raw_sections = re.split(r'(\n{2,}|(?=^#{1,6}\s))', text, flags=re.MULTILINE)
        units = []

        for section in raw_sections:
            section_str = section.strip()
            if not section_str:
                continue
            
            # Nếu đoạn quá dài, tiếp tục phân tách theo câu
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
        """
        Kỹ thuật Chunking thông minh kết hợp Semantic Boundaries & Token Budgeting:
        - Gom nhóm các unit ngữ nghĩa nhỏ thành 1 chunk đạt ngưỡng target_tokens.
        - Giữ cho chunk luôn nhỏ hơn max_tokens để không bị rách Context Window của LLM.
        - Tạo overlap giữa các chunk kề nhau để giữ mạch ngữ cảnh.
        """
        semantic_units = cls.semantic_split_boundaries(text)
        if not semantic_units:
            return []

        chunks = []
        current_chunk_units = []
        current_tokens = 0

        for unit in semantic_units:
            unit_tokens = cls.count_tokens(unit)

            # Trường hợp 1 đơn vị quá lớn (> max_tokens), bắt buộc phải dùng Slided Window cho đơn vị đó
            if unit_tokens > max_tokens:
                if current_chunk_units:
                    chunks.append("\n\n".join(current_chunk_units))
                    current_chunk_units = []
                    current_tokens = 0
                
                # Cắt đơn vị lớn này theo lượng token cố định kèm overlap
                chars_per_token = max(1, len(unit) // unit_tokens)
                chunk_char_size = max_tokens * chars_per_token
                overlap_char_size = overlap_tokens * chars_per_token
                
                for i in range(0, len(unit), chunk_char_size - overlap_char_size):
                    sub_chunk = unit[i:i + chunk_char_size]
                    chunks.append(sub_chunk)
                continue

            # Nếu thêm unit này vào làm vượt quá max_tokens -> Đóng gói chunk hiện tại
            if current_tokens + unit_tokens > max_tokens:
                chunks.append("\n\n".join(current_chunk_units))
                
                # Tạo Overlap bằng cách giữ lại đơn vị cuối cùng của chunk trước
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

            # Nếu đã đủ ngưỡng target_tokens mong muốn
            if current_tokens >= target_tokens:
                chunks.append("\n\n".join(current_chunk_units))
                # Chuẩn bị cho chunk tiếp theo với Overlap
                last_unit = current_chunk_units[-1]
                if cls.count_tokens(last_unit) <= overlap_tokens:
                    current_chunk_units = [last_unit]
                    current_tokens = cls.count_tokens(last_unit)
                else:
                    current_chunk_units = []
                    current_tokens = 0

        # Lưu lại phần dư cuối cùng nếu có
        if current_chunk_units:
            remaining_text = "\n\n".join(current_chunk_units)
            if not chunks or remaining_text != chunks[-1]:
                chunks.append(remaining_text)

        logger.info(f"✂️ [Semantic Chunking] Đã phân rã văn bản ({cls.count_tokens(text)} tokens) thành {len(chunks)} chunks an toàn.")
        return chunks

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """
        Cập nhật hàm chunk_text cũ sử dụng cơ chế Token Budget & Semantic Chunking mới.
        Giữ nguyên interface cũ để tương thích hoàn hảo với mã nguồn hiện tại.
        """
        # Quy đổi ước tính char_size ra token: 1 token ≈ 4 chars
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
        """
        Luồng Knowledge Lifecycle với RawDocument: 
        - Trích xuất file -> Lưu nội dung thô vào RawDocument (staging) -> Chờ AI Auditor phân tích & quản trị viên duyệt.
        """
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
        # Chuẩn hóa kiểm tra trạng thái tương thích với cả Enum và Str
        current_status = getattr(knowledge_chapter, 'status', None)
        if current_status not in [KnowledgeStatus.APPROVED, 'approved', 'APPROVED']:
            logger.warning(f"⛔ [VectorDB] Từ chối commit: Chapter ID {getattr(knowledge_chapter, 'id', None)} chưa ở trạng thái 'approved'.")
            return False

        try:
            chapter_content = getattr(knowledge_chapter, 'content', '')
            if not chapter_content:
                return False

            # Sử dụng Semantic Chunking dựa trên Token Budget cho Vector DB
            chunks = DocumentProcessorService.chunk_by_token_budget(
                text=chapter_content,
                target_tokens=300,
                max_tokens=500,
                overlap_tokens=50
            )
            
            vector_manager = VectorDBManager()
            
            # Xóa các embedding cũ trước khi thêm mới
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
        """
        Alias method nhằm đáp ứng tương thích với Django Signals/Tasks.
        """
        return cls.commit_to_vector_db(knowledge_chapter)

    @classmethod
    def create_draft_chapters_from_raw(cls, raw_document):
        """
        Khởi tạo các KnowledgeChapter ở trạng thái 'pending' từ nội dung thô của RawDocument.
        Tuân thủ tuyệt đối quy tắc Hard Scoping theo group_id và Semantic Chunking.
        """
        from apps.group_chat.models import KnowledgeChapter, KnowledgeUnit
        
        if not raw_document.raw_content:
            return []

        # 1. Tạo một KnowledgeUnit đại diện cho tài liệu upload nếu chưa có
        file_name = os.path.basename(raw_document.document.file.name) if raw_document.document and raw_document.document.file else "Tài liệu"
        knowledge_unit, _ = KnowledgeUnit.objects.get_or_create(
            group_id=raw_document.group_id,
            title=f"Tài liệu: {file_name}",
            defaults={"description": "Được trích xuất tự động bởi hệ thống AI P1 Background."}
        )

        # 2. Chia nhỏ văn bản dựa trên Semantic Boundaries & Token Budget (~400 tokens / chapter nháp)
        chunks = cls.chunk_by_token_budget(
            text=raw_document.raw_content,
            target_tokens=400,
            max_tokens=650,
            overlap_tokens=60
        )
        created_chapters = []

        for index, chunk_text in enumerate(chunks, start=1):
            first_line = chunk_text.split('\n')[0][:60]
            chapter_title = f"Phần {index}: {first_line if first_line else 'Nội dung chi tiết'}"

            chapter = KnowledgeChapter.objects.create(
                group_id=raw_document.group_id,
                unit=knowledge_unit,
                title=chapter_title,
                summary=chunk_text[:300],  # Tóm tắt ngắn
                content=chunk_text,        # Nội dung chi tiết của chương
                status='pending',          # Bắt buộc là pending
                has_conflict=False
            )
            created_chapters.append(chapter)

        logger.info(f"📚 [Knowledge Lifecycle] Đã tạo thành công {len(created_chapters)} KnowledgeChapter (pending) cho RawDoc ID {raw_document.id}")
        return created_chapters