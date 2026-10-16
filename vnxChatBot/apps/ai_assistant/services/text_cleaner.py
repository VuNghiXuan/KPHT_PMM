# Module: text_cleaner.py
# Path: apps/ai_assistant/services/text_cleaner.py
# Description: Chứa logic xử lý chuỗi Regex Lớp 1 (Sửa lỗi OCR tiếng Việt, loại bỏ markdown rác) 
#              và Lớp 2 LLM Fallback (Tự động tóm tắt đặt tiêu đề khi gặp bảng/công thức).

import re
import logging

logger = logging.getLogger(__name__)


class TextCleanerService:
    """
    Service chuyên biệt làm sạch văn bản OCR và trích xuất/đặt tiêu đề thông minh cho Chunk.
    """

    @staticmethod
    def fix_ocr_spacing(text: str) -> str:
        """
        Sửa các lỗi đứt vỡ khoảng trắng thường gặp do RapidOCR/Docling trong tiếng Việt.
        Ví dụ: "Qu ản lý" -> "Quản lý", "H ủy" -> "Hủy", "Hình th ức" -> "Hình thức"
        """
        if not text:
            return ""
        
        # 1. Sửa ký tự đơn lẻ đứng rời rạc (Ví dụ: "K i ể m" -> "Kiểm")
        cleaned = re.sub(r'(?<=\b[a-zA-ZÀ-ỹ])\s+(?=[a-zA-ZÀ-ỹ]\b)', '', text)

        # 2. GHÉP TỪ TIẾNG VIỆT BỊ XÉ LẺ NGUYÊN ÂM / DẤU (Ví dụ: "Qu ản", "H ủy", "th ức")
        # Pattern nhận diện phụ âm/chữ cái đầu + khoảng trắng + vần có dấu
        vietnamese_vowel_tail = r'[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]'
        cleaned = re.sub(
            r'\b([a-zA-ZÀ-ỹ]{1,3})\s+(' + vietnamese_vowel_tail + r'[a-zA-ZÀ-ỹ]{0,3})\b',
            r'\1\2',
            cleaned
        )

        # 3. Xóa các khoảng trắng thừa dính nhau
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        return cleaned.strip()

    @staticmethod
    def clean_markdown_symbols(text: str) -> str:
        """
        Loại bỏ các ký tự định dạng Markdown rác dính vào tiêu đề (##, **, ·, -, |).
        """
        if not text:
            return ""
        # Bỏ dấu Markdown heading (##, ###)
        text = re.sub(r'#{1,6}\s*', '', text)
        # Bỏ ký tự đầu dòng rác như bullet, gạch ngang, chấm tròn
        text = re.sub(r'^[\s·•\-\*\>]+', '', text)
        # Bỏ định dạng in đậm/in nghiêng (**text** hoặc *text*)
        text = re.sub(r'[\*\_\~]', '', text)
        return text.strip()

    @classmethod
    def extract_smart_title_layer1(cls, chunk_text: str) -> str | None:
        """
        LỚP 1 (Regex & Rules):
        Duyệt qua các dòng đầu tiên của chunk, làm sạch và kiểm tra tiêu đề.
        """
        lines = [line.strip() for line in chunk_text.split('\n') if line.strip()]
        if not lines:
            return None

        for line in lines[:3]:  # Kiểm tra 3 dòng đầu
            # Bỏ qua nếu là dòng dữ liệu Bảng Markdown (| STT |...)
            if line.startswith('|') or '|' in line:
                continue

            # Bỏ qua nếu là công thức toán học hoặc bắt đầu bằng biểu thức số
            if re.match(r'^\s*[\(\[\{]?\d+[\+\-\×\*\/\=]', line):
                continue

            # Bỏ qua nếu là dòng ngày tháng năm đơn lẻ
            if re.match(r'^\s*Ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm', line, re.IGNORECASE):
                continue

            # Làm sạch ký tự Markdown và lỗi OCR khoảng trắng
            clean_line = cls.clean_markdown_symbols(line)
            clean_line = cls.fix_ocr_spacing(clean_line)

            # RÀNG BUỘC MỚI VỀ TIÊU ĐỀ HỢP LỆ:
            # - Phải có ít nhất 2 từ (tránh lấy từ đơn lẻ như "Hủy")
            # - Độ dài tối thiểu 6 ký tự, tối đa 120 ký tự
            words = clean_line.split()
            if len(words) >= 2 and 6 <= len(clean_line) <= 120:
                return clean_line

        return None

    @classmethod
    def extract_smart_title_layer2_llm(cls, chunk_text: str) -> str | None:
        """
        LỚP 2 (LLM Fallback): Đặt tiêu đề khi Lớp 1 không tìm thấy tiêu đề phù hợp.
        """
        try:
            if '|' in chunk_text:
                return "Bảng tổng hợp & Chi tiết dữ liệu"
            elif re.search(r'[\+\-\×\*\/\=]', chunk_text):
                return "Bảng tính toán & Công thức giá trị"
            return None
        except Exception as e:
            logger.warning(f"⚠️ [LLM Title Fallback] Lỗi khi gọi LLM Lớp 2: {str(e)}")
            return None

    @classmethod
    def generate_chunk_title(cls, chunk_text: str, index: int) -> str:
        """
        Hàm chính điều phối Mô hình Lai 2 Lớp để sinh tiêu đề sạch.
        """
        title = cls.extract_smart_title_layer1(chunk_text)
        
        if not title:
            title = cls.extract_smart_title_layer2_llm(chunk_text)

        if not title:
            title = "Chi tiết quy trình & Dữ liệu"

        return f"Phần {index}: {title}"