# Module: document_processor.py
# Path: apps/ai_assistant/services/document_processor.py
# Description: Xử lý trích xuất văn bản từ tài liệu sử dụng Docling/Marker, 
#               phân rã khối thông minh dựa trên Token Budget & Semantic Chunking (Bảo vệ Bảng & VBPL),
#               tiêm Ngữ cảnh Đa tầng (Context Injection) và quản lý vòng đời tri thức gắn chặt với group_id.

import os
import re
import logging
from django.conf import settings
from apps.ai_assistant.vector_store import VectorDBManager
from apps.ai_assistant.models.text_choices import KnowledgeStatus
from apps.ai_assistant.services.text_cleaner import TextCleanerService
from ..services.domain_classifier import classify_text_domain

logger = logging.getLogger(__name__)

# Tính chính xác số lượng Token
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
        cơ chế trích xuất Layout-Aware (Docling/Marker), Semantic Chunking bảo toàn Bảng & Pháp lý,
        và tiêm Ngữ cảnh Đa tầng (Context Enrichment) vào ChromaDB.
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
            raw_text = ""
            if ext == '.pdf':
                try:
                    from docling.document_converter import DocumentConverter
                    converter = DocumentConverter()
                    result = converter.convert(file_path)
                    raw_text = result.document.export_to_markdown()
                    logger.info("📄 [Docling] Trích xuất PDF thành công sang Markdown Table chuẩn.")
                except ImportError:
                    logger.warning("⚠️ Thư viện 'docling' chưa được cài đặt. Đang chuyển qua fallback.")
                except Exception as docling_err:
                    logger.warning(f"⚠️ Docling lỗi ({str(docling_err)}). Đang chuyển qua fallback.")

            if not raw_text:
                raw_text = DocumentProcessorService.extract_text_from_file(file_path)

            # Khôi phục khoảng trắng OCR cơ bản
            if hasattr(TextCleanerService, 'fix_ocr_spacing'):
                cleaned_text = TextCleanerService.fix_ocr_spacing(raw_text)
            else:
                cleaned_text = raw_text

            return cleaned_text

        except Exception as e:
            logger.error(f"❌ [Lỗi trích xuất file {file_path}]: {str(e)}")
            return ""

    @staticmethod
    def _extract_table_header(table_text: str) -> str:
        """Trích xuất 2 dòng tiêu đề đầu tiên của Bảng Markdown (Header Row + Separator)."""
        lines = [line.strip() for line in table_text.split('\n') if line.strip().startswith('|')]
        if len(lines) >= 2:
            return f"{lines[0]}\n{lines[1]}"
        return ""

    @classmethod
    def semantic_split_boundaries(cls, text: str) -> list[str]:
        """
        Bóc tách khối ngữ nghĩa thông minh:
        1. Cắt ranh giới tại Heading (1-6 dấu #), Điều [số], Chương [số/La Mã].
        2. Hoạt động tốt ngay cả khi OCR làm mất dấu xuống dòng (\n) hoặc dính liền sau dấu chấm.
        """
        if not text.strip():
            return []

        # Regex tối ưu: Nhận diện điểm cắt linh hoạt ở đầu chuỗi (^), xuống dòng (\n), 
        # khoảng trắng bất kỳ (\s+), hoặc ranh giới từ (\b)
        split_pattern = r'(?=(?:^|\n|\s+|\b)(?:#{1,6}\s+|(?:Điều\s+\d+|Chương\s+[IVXLCDM\d]+)\b))'

        raw_sections = re.split(split_pattern, text, flags=re.IGNORECASE)
        
        # Lọc bỏ các phần tử rỗng và strip khoảng trắng dư thừa
        return [section.strip() for section in raw_sections if section.strip()]

    @classmethod
    def chunk_by_token_budget(
        cls, 
        text: str, 
        target_tokens: int = 800, 
        max_tokens: int = 1200, 
        overlap_tokens: int = 100
    ) -> list[str]:
        """
        Phân rã văn bản theo Token Budget linh hoạt (800 - 1200 tokens).
        Tự động tiêm lại Header Bảng nếu Bảng vượt quá max_tokens.
        """
        semantic_units = cls.semantic_split_boundaries(text)
        if not semantic_units:
            return []

        chunks = []
        current_chunk_units = []
        current_tokens = 0

        for unit in semantic_units:
            unit_tokens = cls.count_tokens(unit)

            # Trường hợp Single Unit quá dài (> max_tokens), ví dụ: Bảng siêu dài hoặc Điều luật lớn
            if unit_tokens > max_tokens:
                if current_chunk_units:
                    chunks.append("\n\n".join(current_chunk_units))
                    current_chunk_units = []
                    current_tokens = 0

                # Kiểm tra nếu là Bảng Markdown
                if '|' in unit and '\n|' in unit:
                    table_header = cls._extract_table_header(unit)
                    lines = [l for l in unit.split('\n') if l.strip()]
                    
                    sub_chunk_lines = []
                    sub_tokens = 0

                    for line in lines:
                        line_tokens = cls.count_tokens(line)
                        if sub_tokens + line_tokens > max_tokens and sub_chunk_lines:
                            chunks.append("\n".join(sub_chunk_lines))
                            # Bắt đầu chunk mới với Table Header được tiêm lại
                            sub_chunk_lines = [table_header, line] if table_header else [line]
                            sub_tokens = cls.count_tokens("\n".join(sub_chunk_lines))
                        else:
                            sub_chunk_lines.append(line)
                            sub_tokens += line_tokens

                    if sub_chunk_lines:
                        chunks.append("\n".join(sub_chunk_lines))
                else:
                    # Cắt theo ký tự an toàn đối với đoạn văn bản thường quá dài
                    chars_per_token = max(1, len(unit) // unit_tokens)
                    chunk_char_size = max_tokens * chars_per_token
                    overlap_char_size = overlap_tokens * chars_per_token

                    for i in range(0, len(unit), chunk_char_size - overlap_char_size):
                        sub_chunk = unit[i:i + chunk_char_size]
                        chunks.append(sub_chunk)
                continue

            if current_tokens + unit_tokens > max_tokens:
                chunks.append("\n\n".join(current_chunk_units))
                current_chunk_units = [unit]
                current_tokens = unit_tokens
            else:
                current_chunk_units.append(unit)
                current_tokens += unit_tokens

            if current_tokens >= target_tokens:
                chunks.append("\n\n".join(current_chunk_units))
                current_chunk_units = []
                current_tokens = 0

        if current_chunk_units:
            remaining_text = "\n\n".join(current_chunk_units)
            if not chunks or remaining_text != chunks[-1]:
                chunks.append(remaining_text)

        logger.info(f"✂️ [Layout-Aware Chunking] Phân rã văn bản ({cls.count_tokens(text)} tokens) thành {len(chunks)} chunks an toàn.")
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

        logger.info(f"⏳ [Knowledge Lifecycle] RawDocument ID {raw_document.id} đang ở 'STAGING' cho Group ID: {raw_document.group_id}")
        return True

    @staticmethod
    def commit_to_vector_db(knowledge_chapter):
        """
        Đồng bộ KnowledgeChapter đã APPROVED vào ChromaDB.
        Tự động tiêm Context Header & Metadata Filtering phục vụ RAG Routing.
        """
        current_status = getattr(knowledge_chapter, 'status', None)
        if current_status not in [KnowledgeStatus.APPROVED, 'approved', 'APPROVED']:
            logger.warning(f"⛔ [VectorDB] Từ chối commit: Chapter ID {getattr(knowledge_chapter, 'id', None)} chưa 'approved'.")
            return False

        try:
            # Ưu tiên lấy suggested_content (chứa 100% công thức, bảng biểu đã làm sạch)
            chapter_content = getattr(knowledge_chapter, 'suggested_content', '') or getattr(knowledge_chapter, 'content', '')
            if not chapter_content:
                logger.warning(f"⚠️ [VectorDB] Chapter ID {getattr(knowledge_chapter, 'id', None)} không có nội dung để index.")
                return False

            # Phân rã Chunk đồng bộ (Target: 800 tokens, Max: 1200 tokens)
            chunks = DocumentProcessorService.chunk_by_token_budget(
                text=chapter_content,
                target_tokens=800,
                max_tokens=1200,
                overlap_tokens=100
            )

            chapter_title = getattr(knowledge_chapter, 'title', 'Tài liệu Nghiệp vụ')
            domain_scope = getattr(knowledge_chapter, 'domain_scope', None)

            # Tự động trích xuất Domain Scope từ Tiêu đề nếu chưa có (VD: "[Đổi vàng Cấn trừ]")
            if not domain_scope:
                match = re.search(r'\[(.*?)\]', chapter_title)
                domain_scope = match.group(1) if match else "Nghiệp vụ Chung"

            # Tiêm Context Header vào nội dung Chunk trước khi tạo Vector Embedding
            enriched_chunks = []
            for chunk in chunks:
                has_table = "Có" if '|' in chunk and '\n|' in chunk else "Không"
                context_header = f"[PHÂN HỆ: {domain_scope.upper()} | CHƯƠNG: {chapter_title} | CÓ BẢNG: {has_table}]\n"
                enriched_chunks.append(context_header + chunk)

            vector_manager = VectorDBManager()
            vector_manager.delete_unit_embeddings(unit_id=knowledge_chapter.id, group_id=knowledge_chapter.group_id)

            chunks_metadatas = [
                {
                    "chapter_id": str(knowledge_chapter.id),
                    "group_id": str(knowledge_chapter.group_id),
                    "domain_scope": domain_scope,
                    "chunk_index": i
                }
                for i in range(len(enriched_chunks))
            ]

            vector_manager.add_texts(
                texts=enriched_chunks, 
                metadatas=chunks_metadatas,
                group_id=knowledge_chapter.group_id
            )

            logger.info(f"✅ [VectorDB] Đã index thành công {len(enriched_chunks)} enriched chunks cho Chapter ID {knowledge_chapter.id} (Domain: {domain_scope})")
            return True

        except Exception as e:
            logger.error(f"❌ [VectorDB Error] Lỗi đồng bộ Vector cho Chapter ID {knowledge_chapter.id}: {str(e)}")
            return False

    @classmethod
    def commit_chapter_to_vector_db(cls, knowledge_chapter):
        return cls.commit_to_vector_db(knowledge_chapter)

    @classmethod
    def create_draft_chapters_from_raw(cls, raw_document):
        """
        Khởi tạo các KnowledgeChapter từ RawDocument với cơ chế Phê duyệt Tự động (Auto-Approve):
        - Tự động phân loại Phân hệ bằng Cosine Similarity (classify_text_domain).
        - Gắn Source Metadata (file_name, domain) phục vụ AI trích dẫn nguồn.
        - Nếu KHÔNG xung đột AND confidence_score >= 0.8 -> Tự động duyệt ('approved') -> Kích hoạt Signal sync VectorDB.
        - Nếu CÓ xung đột -> Trạng thái 'conflict_detected' -> Đưa vào danh sách chờ Admin.
        - Trường hợp còn lại -> Trạng thái 'pending'.
        """
        from apps.group_chat.models import KnowledgeChapter
        from apps.ai_assistant.models.text_choices import KnowledgeStatus
        from apps.ai_assistant.services.domain_classifier import classify_text_domain

        doc_id = getattr(raw_document, 'id', 'N/A')
        group_id = getattr(raw_document, 'group_id', 'N/A')
        original_filename = getattr(raw_document, 'original_filename', 'Tài liệu không tên')

        if not raw_document.raw_content:
            logger.error(f"❌ [Step 1 Fail] RawDocument ID {doc_id} không có nội dung thô.")
            return []

        logger.info(f"=================== 🚀 BẮT ĐẦU XỬ LÝ RAW DOCUMENT ID: {doc_id} (Group: {group_id}) ===================")
        
        # --- BƯỚC 1: KIỂM TRA NỘI DUNG THÔ ---
        raw_text_length = len(raw_document.raw_content)
        raw_tokens = cls.count_tokens(raw_document.raw_content)
        logger.info(f"📄 [STEP 1 - RAW TEXT]: Độ dài: {raw_text_length} ký tự (~{raw_tokens} tokens).")
        logger.debug(f"🔍 [Sample 200 chars đầu]: {raw_document.raw_content[:200]}...")

        # --- BƯỚC 2: XÁC ĐỊNH NGÀNH & PHÂN HỆ CHÍNH ---
        doc_context = TextCleanerService.extract_document_main_context(raw_document.raw_content)
        logger.info(f"🏷️ [STEP 2 - CONTEXT SCOPE]: Phân hệ trích xuất = {doc_context}")

        # --- BƯỚC 3: PHÂN RÃ CHUNK (SEMANTIC CHUNKING) ---
        chunks = cls.chunk_by_token_budget(
            text=raw_document.raw_content,
            target_tokens=800,
            max_tokens=1200,
            overlap_tokens=100
        )
        logger.info(f"✂️ [STEP 3 - CHUNKING]: Đã chia tài liệu thành {len(chunks)} chunks.")

        created_chapters = []

        # Lấy độ tin cậy trích xuất từ tài liệu (mặc định 0.9 nếu trích xuất thành công)
        confidence_score = getattr(raw_document, 'confidence_score', 0.9)

        # --- BƯỚC 4: XỬ LÝ TỪNG CHUNK QUA LLM VÀ LƯU DB ---
        for index, chunk_text in enumerate(chunks, start=1):
            chunk_tokens = cls.count_tokens(chunk_text)
            logger.info(f"\n--- 🔍 [PROCESSING CHUNK {index}/{len(chunks)}] ({chunk_tokens} tokens) ---")
            logger.info(f"📥 [Input Chunk {index} Sample]: {chunk_text[:120]}...")

            # Gọi Ollama / Cleaner
            raw_title, chapter_summary, cleaned_content = TextCleanerService.process_chunk_with_ollama(
                raw_chunk=chunk_text, 
                index=index,
                doc_context=doc_context
            )

            # 🎯 1. PHÂN LOẠI PHÂN HỆ BẰNG COSINE SIMILARITY
            matched_domain = classify_text_domain(cleaned_content)
            if matched_domain:
                domain_name = matched_domain.name
                domain_code = matched_domain.code
                logger.info(f"🎯 [DOMAIN MATCH]: Đã phân loại vào Phân hệ '{domain_name}' (Code: {domain_code})")
            else:
                domain_name = "Nghiệp vụ Chung"
                domain_code = "GENERAL"
                logger.info("ℹ️ [DOMAIN MATCH]: Không đạt ngưỡng độ tương đồng, gán nhãn mặc định 'Nghiệp vụ Chung'")

            # 🏷️ 2. CHUẨN HÓA TIÊU ĐỀ THEO PHÂN HỆ
            clean_raw_title = raw_title.replace("[Nghiệp vụ Chung]", "").strip()
            chapter_title = f"Phần {index}: [{domain_name}] {clean_raw_title}"

            logger.info(f"📌 [Output Title]   : {chapter_title}")
            logger.info(f"📝 [Output Summary] : {chapter_summary}")
            logger.info(f"📄 [Output Content] : {len(cleaned_content)} chars | Sample: {cleaned_content[:100]}...")

            if cleaned_content == chapter_summary:
                logger.warning(f"⚠️ [WARNING CHUNK {index}]: Nội dung chi tiết bị trùng 100% với Tóm tắt!")

            # 🛑 3. ĐÁNH GIÁ TRẠNG THÁI TỰ ĐỘNG (AUTO-APPROVE RULE)
            has_conflict = False

            if not has_conflict and confidence_score >= 0.8:
                initial_status = KnowledgeStatus.APPROVED
            elif has_conflict:
                initial_status = KnowledgeStatus.CONFLICT_DETECTED
            else:
                initial_status = KnowledgeStatus.PENDING

            # 📌 4. TẠO METADATA TRÍCH DẪN NGUỒN TÀI LIỆU
            source_metadata = {
                "file_name": original_filename,
                "raw_document_id": doc_id,
                "domain_name": domain_name,
                "domain_code": domain_code
            }

            # 💾 5. LƯU CSDL
            chapter = KnowledgeChapter.objects.create(
                group_id=raw_document.group_id,
                title=chapter_title,                 # Tiêu đề linh hoạt theo Domain
                summary=chapter_summary,             # Tóm tắt
                suggested_content=cleaned_content,   # Nội dung do AI đề xuất
                status=initial_status,               # Trạng thái tự động
                has_conflict=has_conflict,
                metadata=source_metadata             # 👈 Sử dụng trường 'metadata' đúng theo Model
            )
            created_chapters.append(chapter)
            logger.info(f"💾 [STEP 4 - SAVE DB]: Đã tạo KnowledgeChapter ID={chapter.id} [Status: '{initial_status}'] thành công.")

        logger.info(f"=================== 🎉 HOÀN THÀNH XỬ LÝ RAW DOCUMENT ID: {doc_id} ===================\n")
        return created_chapters