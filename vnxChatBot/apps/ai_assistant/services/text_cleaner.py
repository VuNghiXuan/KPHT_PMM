# Module: text_cleaner.py
# Path: apps/ai_assistant/services/text_cleaner.py
# Description: Làm sạch văn bản OCR, chuẩn hóa Bảng Markdown toàn cục, 
#               giải mã HTML Entities và sinh Tiêu đề/Tóm tắt giàu ngữ cảnh nghiệp vụ.

import re
import html
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TextCleanerService:
    """
    Service làm sạch chuyên sâu cho VNXCHATBOT.
    Đảm bảo:
    1. Bẻ dòng Bảng Markdown toàn cục (chuyển || thành \n|).
    2. Giải mã HTML Entities (&lt; -> <, &gt; -> >).
    3. Tiêm Context Scope vào Tiêu đề để RAG Vector Store nhận diện chính xác nghiệp vụ.
    4. Tách biệt 100% giữa Tóm tắt (Summary) và Nội dung Chi tiết (Suggested Content).
    """

    @staticmethod
    def fix_ocr_spacing(text: str) -> str:
        """Khôi phục khoảng trắng và ký tự Tiếng Việt bị vỡ do OCR."""
        if not text:
            return ""
        text = html.unescape(text)
        cleaned = re.sub(r'(?<=\b[a-zA-ZÀ-ỹ])\s+(?=[a-zA-ZÀ-ỹ]\b)', '', text)
        vietnamese_vowel_tail = r'[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]'
        cleaned = re.sub(
            r'\b([a-zA-ZÀ-ỹ]{1,3})\s+(' + vietnamese_vowel_tail + r'[a-zA-ZÀ-ỹ]{0,3})\b',
            r'\1\2',
            cleaned
        )
        return re.sub(r'[ \t]+', ' ', cleaned).strip()

    @staticmethod
    def format_markdown_tables(text: str) -> str:
        """
        Bẻ dòng Bảng Markdown toàn cục (Global Table Formatter).
        Khôi phục các bảng bị nén dòng '||' hoặc dính tiêu đề '##'.
        """
        if not text:
            return ""

        raw_text = html.unescape(text).strip()

        # 1. Tách thẻ Heading (##) dính liền với nội dung
        formatted = re.sub(r'(?<!\n)(#{1,6}\s+)', r'\n\n\1', raw_text)

        if '|' not in formatted:
            return formatted

        # 2. Bẻ dòng toàn cục: Thay mọi '||', '|| |', '| |' thành '\n|'
        formatted = re.sub(r'\|\s*\|\s*\|?', '|\n|', formatted)

        # 3. Đảm bảo dòng phân cách tiêu đề bảng (|---|---|) có dòng riêng biệt
        formatted = re.sub(r'(\|\s*:-{2,}:?\s*)+(?=\|)', r'\g<0>\n', formatted)

        # 4. Chuẩn hóa từng dòng
        lines = formatted.split('\n')
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                cleaned_lines.append("")
                continue

            if '|' in line_str:
                if not line_str.startswith('|') and not line_str.startswith('#'):
                    parts = line_str.split('|', 1)
                    if parts[0].strip():
                        cleaned_lines.append(parts[0].strip())
                    line_str = '|' + parts[1]

                if line_str.startswith('|'):
                    if not line_str.endswith('|'):
                        line_str = line_str + ' |'
                    line_str = re.sub(r'\s*\|\s*', ' | ', line_str)

            cleaned_lines.append(line_str)

        return re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned_lines)).strip()

    @classmethod
    def extract_document_main_context(cls, full_document_text: str) -> dict:
        """
        Dùng LLM tự động xác định phân hệ nghiệp vụ chính từ nội dung tài liệu.
        Không hardcode từ khóa.
        """
        if not full_document_text or not full_document_text.strip():
            return {"domain_scope": "Nghiệp vụ Chung"}

        # Lấy 10 dòng đầu tiên làm mẫu ngữ cảnh
        first_lines = full_document_text.strip().split('\n')[:10]
        sample_header = html.unescape(" ".join(first_lines)).strip()[:500]

        ollama_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
        model_name = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b')
        endpoint = f"{ollama_url.rstrip('/')}/api/generate"

        prompt = (
            "Bạn là chuyên gia phân tích tài liệu.\n"
            "Hãy đọc đoạn mở đầu tài liệu sau và xác định ngắn gọn PHÂN HỆ NGHIỆP VỤ CHÍNH (tối đa 2-4 từ).\n"
            "Ví dụ trả về: Hợp đồng lao động, Bảo hành thiết bị, Quản lý kho, Mua bán vàng mới...\n"
            "CHỈ TRẢ VỀ TÊN PHÂN HỆ, KHÔNG BỔ SUNG LỜI DẪN.\n\n"
            f"Đoạn văn bản:\n{sample_header}"
        )

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 20}
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            if response.status_code == 200:
                scope = response.json().get('response', '').strip()
                # Làm sạch kết quả trả về từ LLM
                scope = re.sub(r'[\"\*\#\.\:]', '', scope).strip()
                if scope and len(scope) <= 40:
                    return {"domain_scope": scope}
        except Exception as e:
            logger.warning(f"⚠️ [Ollama Context Warning] {str(e)}. Dùng fallback mặc định.")

        return {"domain_scope": "Nghiệp vụ Chung"}

    @classmethod
    def process_chunk_with_ollama(
        cls, 
        raw_chunk: str, 
        index: int, 
        doc_context: str | dict = "Nghiệp vụ Chung"
    ) -> tuple[str, str, str]:
        """
        Xử lý 2 tầng:
        1. Bẻ dòng Bảng Markdown & Giải mã HTML 100% cho `cleaned_content`.
        2. Sinh Tiêu đề & Tóm tắt qua Ollama với bóc tách Regex an toàn và Fuzzy Parser dự phòng.
        """
        domain_scope = doc_context.get('domain_scope', 'Nghiệp vụ Chung') if isinstance(doc_context, dict) else str(doc_context)
        
        cleaned_content = cls.format_markdown_tables(raw_chunk)
        det_title, det_summary = cls.extract_deterministic_title_and_summary(cleaned_content, index, domain_scope)

        if not raw_chunk or not raw_chunk.strip():
            return det_title, det_summary, cleaned_content

        ollama_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
        model_name = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b')
        endpoint = f"{ollama_url.rstrip('/')}/api/generate"

        sample_text = cleaned_content[:650].strip()

        prompt = (
            f"Bạn là chuyên gia phân tích tài liệu ({domain_scope}).\n"
            "Hãy đọc đoạn văn bản sau và cung cấp 2 thông tin:\n"
            "1. TIÊU ĐỀ: Đặt MỘT tiêu đề ngắn gọn (4-8 từ) nêu rõ nội dung chính.\n"
            "2. TÓM TẮT: Viết 1-2 câu tóm tắt bản chất nội dung.\n\n"
            "ĐỊNH DẠNG TRẢ VỀ BẮT BUỘC:\n"
            "[TITLE] Tiêu đề ở đây [/TITLE]\n"
            "[SUMMARY] Câu tóm tắt ở đây [/SUMMARY]\n\n"
            f"Văn bản:\n{sample_text}"
        )

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 250,
                "temperature": 0.1,
                "top_p": 0.85
            }
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=60)
            if response.status_code == 200:
                result_text = response.json().get('response', '').strip()
                logger.debug(f"🤖 [Ollama Raw Output Chunk {index}]: {result_text}")

                # 💡 1. BỐC TÁCH REGEX CHUẨN XÁC: Escape đầy đủ cả [TITLE] và [SUMMARY] Escape đúng cả \[ và \]                                
                title_match = re.search(r'\[TITLE\]\s*(.*?)(?:\[/?TITLE\]|\[/?SUMMARY\]|\n|$)', result_text, re.IGNORECASE)
                summary_match = re.search(r'\[SUMMARY\]\s*(.*?)(?:\[/?SUMMARY\]|$)', result_text, re.IGNORECASE | re.DOTALL)

                raw_title = title_match.group(1).strip() if title_match else ""
                raw_summary = summary_match.group(1).strip() if summary_match else ""

                # 🔮 2. FUZZY PARSER: Dự phòng khi Ollama không dùng đúng thẻ [TITLE] / [SUMMARY]
                if not raw_title or not raw_summary:
                    lines = [line.strip() for line in result_text.split('\n') if line.strip()]
                    
                    for line in lines:
                        # Tìm Tiêu đề dạng: "Tiêu đề: ...", "1. Tiêu đề: ...", "Title: ..."
                        if not raw_title:
                            m_title = re.search(r'^(?:\d+[\.\)]\s*)?(?:tiêu đề|title)\s*[:\-]\s*(.*)', line, re.IGNORECASE)
                            if m_title:
                                raw_title = m_title.group(1)
                                continue

                        # Tìm Tóm tắt dạng: "Tóm tắt: ...", "Summary: ..."
                        if not raw_summary:
                            m_summary = re.search(r'^(?:\d+[\.\)]\s*)?(?:tóm tắt|summary)\s*[:\-]\s*(.*)', line, re.IGNORECASE)
                            if m_summary:
                                raw_summary = m_summary.group(1)
                                continue

                    # Trường hợp Ollama chỉ trả về văn bản tự do: Lấy dòng 1 làm Tiêu đề, các dòng sau làm Tóm tắt
                    if not raw_title and lines:
                        raw_title = lines[0]
                    if not raw_summary and len(lines) > 1:
                        raw_summary = " ".join(lines[1:])

                # 🧼 3. LÀM SẠCH TIÊU ĐỀ
                clean_title = re.sub(r'[\"\*\#\|\:\-\_<>\[\]]', '', raw_title).strip()
                clean_title = re.sub(r'^(tiêu đề|title|phần \d+)\s*[:\-]\s*', '', clean_title, flags=re.IGNORECASE).strip()
                clean_title = re.sub(r'(title|summary)$', '', clean_title, flags=re.IGNORECASE).strip()

                # 🧼 4. LÀM SẠCH TÓM TẮT
                clean_summary = html.unescape(raw_summary).strip()
                clean_summary = re.sub(r'[\"\*\#|<>\[\]]', '', clean_summary).strip()
                clean_summary = re.sub(r'^(tóm tắt|summary)\s*[:\-]\s*', '', clean_summary, flags=re.IGNORECASE).strip()

                final_title = f"Phần {index}: [{domain_scope}] {clean_title}" if clean_title else det_title
                final_summary = clean_summary if len(clean_summary) >= 15 else det_summary

                return final_title, final_summary, cleaned_content

        except Exception as e:
            logger.warning(f"⚠️ [Ollama Warning] {str(e)}. Sử dụng kết quả Deterministic.")

        return det_title, det_summary, cleaned_content

    @classmethod
    def extract_deterministic_title_and_summary(
        cls, 
        cleaned_content: str, 
        index: int, 
        doc_context: str | dict
    ) -> tuple[str, str]:
        """
        Bóc tách Tiêu đề & Tóm tắt theo thuật toán Deterministic (Fallback khi Ollama offline).
        """
        domain_scope = doc_context.get('domain_scope', 'Nghiệp vụ Chung') if isinstance(doc_context, dict) else str(doc_context)

        if not cleaned_content:
            return f"Phần {index}: [{domain_scope}] Chi tiết quy trình", f"Thông tin chi tiết quy trình cho {domain_scope}."

        lines = [line.strip() for line in cleaned_content.split('\n') if line.strip()]

        # --- 1. TRÍCH XUẤT TIÊU ĐỀ ---
        extracted_title = None

        for line in lines:
            if line.startswith('#'):
                clean_h = re.sub(r'[\#\*\n\|]', '', line).strip()
                clean_h = re.sub(r'^\d+[\.\)]\s*', '', clean_h)
                if len(clean_h) >= 3 and clean_h.lower() not in ["tính tiền thanh toán:", "tính tiền:"]:
                    extracted_title = clean_h[:60]
                    break

        if not extracted_title:
            for line in lines:
                if not line.startswith('|') and len(line) >= 8:
                    clean_l = re.sub(r'[\#\*\n]', '', line).strip()
                    if clean_l.lower() not in ["tính tiền thanh toán:", "ghi chú:"]:
                        extracted_title = clean_l[:60]
                        break

        if not extracted_title:
            for line in lines:
                if line.startswith('|'):
                    cells = [c.strip() for c in line.split('|') if c.strip() and '---' not in c]
                    if cells:
                        extracted_title = " - ".join(cells[:3])[:60]
                        break

        if extracted_title:
            title = f"Phần {index}: [{domain_scope}] {extracted_title}"
        else:
            title = f"Phần {index}: [{domain_scope}] Quy định & Chi tiết nghiệp vụ"

        # --- 2. TRÍCH XUẤT TÓM TẮT DỰ PHÒNG CHUẨN HÓA ---
        summary = f"Nội dung chi tiết thuộc phân hệ {domain_scope} (Phần {index}), bao gồm các quy định và thông tin chi tiết liên quan."

        return title, summary

    @classmethod
    def generate_chunk_title(cls, chunk_text: str, index: int) -> str:
        title, _, _ = cls.process_chunk_with_ollama(chunk_text, index)
        return title