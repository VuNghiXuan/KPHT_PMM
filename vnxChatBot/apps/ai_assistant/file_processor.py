"""
Mục đích: Trích xuất text từ đa dạng định dạng file (docx, xlsx, csv, pdf, hình ảnh, txt).
Tác giả: Kiến trúc sư VnxChatBot
Liên kết: Được gọi bởi ai_assistant.services.rag_engine khi có tài liệu mới.
"""
import docx
import pandas as pd
import easyocr
import fitz  # PyMuPDF để xử lý PDF
from pathlib import Path

class FileProcessor:
    """
    Service trích xuất text tập trung.
    Tại sao: Giảm tải cho LLM bằng cách tiền xử lý tại Local, giảm token sử dụng.
    """
    
    @staticmethod
    def process_txt(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def process_docx(file_path):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    @staticmethod
    def process_excel(file_path):
        df = pd.read_excel(file_path)
        return df.to_markdown()

    @staticmethod
    def process_csv(file_path):
        """Xử lý file CSV."""
        df = pd.read_csv(file_path)
        return df.to_markdown()

    @staticmethod
    def process_pdf(file_path):
        """Trích xuất text từ PDF sử dụng PyMuPDF."""
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    @staticmethod
    def process_image(file_path):
        reader = easyocr.Reader(['vi', 'en'], gpu=False)
        result = reader.readtext(file_path, detail=0)
        return " ".join(result)

def extract_text_from_file(file_path: str) -> str:
    """
    Điều hướng xử lý file đa định dạng.
    """
    ext = Path(file_path).suffix.lower()
    
    mapping = {
        '.txt': FileProcessor.process_txt,
        '.docx': FileProcessor.process_docx,
        '.xlsx': FileProcessor.process_excel,
        '.csv': FileProcessor.process_csv,
        '.pdf': FileProcessor.process_pdf,
        '.png': FileProcessor.process_image,
        '.jpg': FileProcessor.process_image,
        '.jpeg': FileProcessor.process_image
    }
    
    processor = mapping.get(ext)
    return processor(file_path) if processor else "Định dạng không được hỗ trợ."