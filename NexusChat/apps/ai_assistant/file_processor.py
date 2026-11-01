"""
File: apps/ai_assistant/processor.py
Mục đích: Trích xuất text từ các định dạng file (docx, xlsx, hình ảnh, txt) để phục vụ RAG.
Liên kết: Được gọi bởi ai_assistant.services khi có tài liệu mới.
"""
import docx
import pandas as pd
import easyocr
from pathlib import Path

class FileProcessor:
    """
    Service trích xuất text từ file.
    Vai trò: Chuyển đổi dữ liệu thô sang định dạng Text/Markdown để tối ưu token cho AI.
    """
    
    @staticmethod
    def process_txt(file_path):
        """Trích xuất text từ file .txt với encoding UTF-8."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def process_docx(file_path):
        """Trích xuất text từ file .docx."""
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    @staticmethod
    def process_excel(file_path):
        """Trích xuất dữ liệu Excel sang định dạng Markdown."""
        df = pd.read_excel(file_path)
        return df.to_markdown()

    @staticmethod
    def process_image(file_path):
        """Trích xuất text từ hình ảnh sử dụng EasyOCR (Local processing)."""
        reader = easyocr.Reader(['vi', 'en'], gpu=False) # Cấu hình gpu=True nếu server có hỗ trợ CUDA
        result = reader.readtext(file_path, detail=0)
        return " ".join(result)

def extract_text_from_file(file_path: str) -> str:
    """
    Hàm điều hướng xử lý file dựa trên phần mở rộng.
    
    Args:
        file_path: Đường dẫn vật lý của tệp tin.
        
    Returns:
        str: Nội dung text đã được trích xuất.
    """
    ext = Path(file_path).suffix.lower()
    
    mapping = {
        '.txt': FileProcessor.process_txt,
        '.docx': FileProcessor.process_docx,
        '.xlsx': FileProcessor.process_excel,
        '.png': FileProcessor.process_image,
        '.jpg': FileProcessor.process_image,
        '.jpeg': FileProcessor.process_image
    }
    
    processor = mapping.get(ext)
    if processor:
        return processor(file_path)
    return ""