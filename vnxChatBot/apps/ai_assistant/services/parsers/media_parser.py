import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class VisionParser:
    """Parser xử lý hình ảnh tài liệu quét (PNG, JPG) sử dụng OCR / Vision Model."""
    
    def parse(self, file_path):
        file_name = Path(file_path).name
        logger.info(f"👁️ [VisionParser] Đang thực hiện OCR cho file ảnh: {file_name}")
        # Tích hợp OCR Engine tại đây
        return [{
            "content": f"[Nội dung trích xuất từ ảnh OCR: {file_name}]",
            "metadata": {"source_file": file_name, "parser_type": "vision_ocr"}
        }]


class HTMLParser:
    """Parser làm sạch và trích xuất nội dung văn bản từ trang HTML."""
    
    def parse(self, file_path):
        file_name = Path(file_path).name
        logger.info(f"🌐 [HTMLParser] Đang làm sạch mã HTML của file: {file_name}")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
            
        return [{
            "content": f"[Nội dung HTML đã làm sạch từ: {file_name}]\n{html_content[:2000]}",
            "metadata": {"source_file": file_name, "parser_type": "html_clean"}
        }]