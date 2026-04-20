import os
import requests
import json
from groq import Groq
from google import genai
from dotenv import load_dotenv

load_dotenv()

class AIManager:
    def __init__(self, provider=None):
        """
        Khởi tạo quản lý bộ não AI chuyên biệt cho soạn thảo quy trình HTJ.
        """
        # Mặc định lấy từ .env nếu GUI không truyền vào
        if provider:
            self.provider = provider.lower()
        else:
            self.provider = os.getenv("DEFAULT_PROVIDER", "groq").lower()

    def set_provider(self, provider_name):
        """Cập nhật bộ não AI từ giao diện (Groq, Gemini, Ollama)"""
        self.provider = provider_name.lower()

    def _call_ai_api(self, prompt):
        """
        Hàm cốt lõi để gọi các bộ não khác nhau.
        Chỉ trả về văn bản thuần túy (Quy trình, phân tích).
        """
        provider = self.provider.lower()
        
        try:
            # 1. GROQ: Ưu điểm là phản hồi cực nhanh (Llama 3.3)
            if provider == "groq":
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_name,
                    temperature=0.2 # Thấp để đảm bảo tính chính xác cho tiệm vàng
                )
                return completion.choices[0].message.content

            # 2. GEMINI: Ưu điểm là hiểu ngữ cảnh tiếng Việt và dữ liệu lớn rất tốt
            elif provider == "gemini":
                client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text

            # 3. OLLAMA: Chạy nội bộ (Local), bảo mật dữ liệu tuyệt đối
            elif provider == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
                model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
                
                url = f"{base_url}/api/generate"
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
                
                response = requests.post(url, json=payload, timeout=90)
                response.raise_for_status()
                return response.json().get("response", "")

        except Exception as e:
            return f"❌ Lỗi kết nối bộ não [{provider}]: {str(e)}"
        
        return "⚠️ Không xác định được bộ não xử lý."

    def generate_htj_procedure(self, sheet_name, clean_text):
        """
        Prompt thông minh: Tự động nhận diện nghiệp vụ và thiết lập logic hệ thống.
        """
        prompt = f"""
    Bạn là Chuyên gia Phân tích Nghiệp vụ (BA) và Tư vấn Giải pháp cho hệ thống quản lý vàng HTJ Jewelry.
    Dữ liệu dưới đây trích xuất từ cấu trúc module: "{sheet_name}"

    DỮ LIỆU ĐẦU VÀO:
    {clean_text}

    NHIỆM VỤ CỦA BẠN:
    1. **Xác định Nghiệp vụ:** Dựa vào tên các chức năng, hãy xác định đây là nhóm nghiệp vụ nào (Ví dụ: Mua bán lẻ, Quản lý kho sỉ, Cầm đồ, Thu chi hộ, hay Chế tác...).
    2. **Phân tích Luồng Dữ liệu (Data Flow):** - Những thông tin nào là đầu vào (Input)? 
    - Những thông tin nào là kết quả tính toán (Output)?
    - Mối quan hệ giữa các Module này là gì?
    3. **Thiết lập Quy trình Vận hành Chuẩn (SOP):** Thiết lập quy trình từng bước để thực hiện nghiệp vụ này trên phần mềm, từ lúc bắt đầu nhập liệu đến khi kết thúc giao dịch và lưu kho.
    4. **Logic & Công thức:** - Đề xuất các công thức tính toán tự động dựa trên đặc thù ngành vàng (Tuổi vàng, Trọng lượng thực, Trọng lượng quy, Tiền công, Thuế VAT).
    - Lưu ý: Phân biệt rõ công thức cho "Vàng nguyên liệu" và "Nữ trang thành phẩm".
    5. **Kiểm soát Rủi ro & Cảnh báo (Validation Rules):**
    - Đề xuất các điều kiện chặn lỗi (Ví dụ: Trọng lượng không được âm, Tiền mặt không đủ không cho xuất hóa đơn...).
    - Các điểm cần đối soát (Reconciliation) để tránh thất thoát tiền và vàng.

    YÊU CẦU TRÌNH BÀY:
    - Sử dụng thuật ngữ chuyên ngành kim hoàn (Ví dụ: Vàng gốc, Vàng trung gian, Tiền công, Độ phân kim...).
    - Trình bày dạng Markdown với các tiêu đề rõ ràng, súc tích để nhân viên dễ đọc.
    """
        return self._call_ai_api(prompt)