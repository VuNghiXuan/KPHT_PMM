import logging
from pathlib import Path
from .parsers.excel_parser import ExcelSemanticParser
from .parsers.docling_parser import DoclingParser
from .parsers.media_parser import VisionParser, HTMLParser

logger = logging.getLogger(__name__)

class DocumentParserService:
    """
    Service điều phối trung gian (Orchestrator) giúp phân tích đa định dạng tài liệu
    thành cấu trúc Markdown/JSON chuẩn hóa trước khi đưa vào vòng đời kiểm duyệt.
    """
    
    @staticmethod
    def get_parser_for_file(file_extension: str):
        """Chọn parser chuyên dụng dựa trên định dạng file với cơ chế fallback an toàn."""
        clean_ext = file_extension.lower().lstrip('.')
        
        parsers = {
            'pdf': DoclingParser(),      # Tốt cho văn bản pháp luật, giữ hierarchy (Điều, Khoản)
            'docx': DoclingParser(),     # Giữ cấu trúc phân cấp văn bản Word tốt
            'xlsx': ExcelSemanticParser(),   # Chuyển Excel thành Markdown Table theo row-chunks
            'xls': ExcelSemanticParser(),    # Hỗ trợ định dạng Excel cũ
            'png': VisionParser(),       # OCR/Vision cho ảnh chứa tài liệu quét
            'jpg': VisionParser(),
            'jpeg': VisionParser(),
            'html': HTMLParser(),        # Làm sạch và trích xuất nội dung HTML thô
        }
        
        parser = parsers.get(clean_ext)
        if not parser:
            logger.warning(f"⚠️ [ParserService] Không tìm thấy parser chuyên dụng cho đuôi file: '.{clean_ext}'. Sử dụng mặc định DoclingParser.")
            return DoclingParser()
        return parser

    @classmethod
    def parse_document(cls, file_path: str):
        """
        Phương thức chính để gọi bóc tách file dựa trên phần mở rộng.
        Trả về danh sách các chunk dữ liệu chuẩn hóa dạng dict: 
        [{"content": "...", "metadata": {...}}]
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            logger.error(f"❌ [ParserService] Không tìm thấy file tại đường dẫn: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path_obj.suffix
        parser = cls.get_parser_for_file(ext)
        
        logger.info(f"🔄 [ParserService] Đang sử dụng {parser.__class__.__name__} để bóc tách: {path_obj.name}")
        
        try:
            chunks = parser.parse(file_path)
            
            # Chuẩn hóa metadata tầng Service đảm bảo không thiếu thông tin định danh
            normalized_chunks = []
            for idx, chunk in enumerate(chunks, start=1):
                content = chunk.get("content", "")
                metadata = chunk.get("metadata", {})
                
                # Bổ sung metadata bắt buộc cho vòng đời tri thức
                metadata.setdefault("source_file", path_obj.name)
                metadata.setdefault("parser_type", parser.__class__.__name__)
                metadata.setdefault("chunk_index", idx)
                
                normalized_chunks.append({
                    "content": content,
                    "metadata": metadata
                })
                
            return normalized_chunks
            
        except Exception as e:
            logger.exception(f"❌ [ParserService] Lỗi nghiêm trọng khi bóc tách file {path_obj.name}: {str(e)}")
            raise RuntimeError(f"Document parsing failed: {str(e)}")