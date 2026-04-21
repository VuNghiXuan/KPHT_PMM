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
                
                response = requests.post(url, json=payload, timeout=300)
                response.raise_for_status()
                return response.json().get("response", "")

        except Exception as e:
            return f"❌ Lỗi kết nối bộ não [{provider}]: {str(e)}"
        
        return "⚠️ Không xác định được bộ não xử lý."

   

    def generate_htj_procedure(self, sheet_name, clean_text):
        prompt = f"""
    Bạn là một Chuyên gia Phân tích Nghiệp vụ (BA) cực kỳ khắt khe cho hệ thống HTJ Jewelry.
    NHIỆM VỤ: Chuyển đổi cấu trúc dữ liệu dưới đây thành quy trình hướng dẫn sử dụng.

    DỮ LIỆU THỰC TẾ TRONG FILE (CONTEXT):
    "{clean_text}"

    ⚠️ NGUYÊN TẮC "SỐNG CÒN" KHI BIÊN SOẠN:
    1. KHÔNG ĐƯỢC TỰ CHẾ: Tuyệt đối không thêm bất kỳ nút bấm, cột dữ liệu hay thuật ngữ nào không có trong phần "DỮ LIỆU THỰC TẾ". Nếu file không có "Tuổi bù", không được nhắc tới.
    2. TRUNG THÀNH VỚI GIAO DIỆN: Nếu trong dữ liệu ghi nút là "Phân bổ chi phí", phải dùng đúng cụm từ đó. Không được thay bằng "Tính toán" hay "Chia tiền".
    3. PHÂN BIỆT RÕ FORM: 
    - Cái nào nằm ở cột "Module" (thường là tên Form/Popup).
    - Cái nào nằm ở cột "Chức năng/Trường dữ liệu" (thành phần bên trong Form).

    CẤU TRÚC BẢN VIẾT PHẢI THEO ĐÚNG THỨ TỰ SAU:

    1. **Mô tả mục đích Form:** Form "{sheet_name}" này dùng để làm gì? (Chỉ suy luận dựa trên các tên cột hiện có).

    2. **Trình tự thao tác thực tế (Step-by-Step):**
    - Phân tích từ dữ liệu để chỉ ra: Bước 1 mở Form nào, Bước 2 nhấn nút gì (tên nút phải khớp 100%), Bước 3 nhập vào ô nào.
    - Chỉ rõ ô nào là [Nhập tay], ô nào là [Hệ thống tự hiển thị/Tính toán] dựa trên logic ngành vàng của các cột đó.

    3. **Từ điển các trường dữ liệu (Glossary):**
    - Chỉ giải thích những thuật ngữ xuất hiện trong bảng dữ liệu trên. Giải thích rõ ý nghĩa kỹ thuật của chúng trong Form này.

    4. **Kiểm soát nhập liệu (Validation Rules):**
    - Dựa trên tên cột, hãy đưa ra quy tắc chặn lỗi thực tế (Ví dụ: Nếu có cột 'Trọng lượng' thì không được nhập âm hoặc bằng 0).
    - Chỉ rõ khi nhấn nút [Ghi dữ liệu/Lưu] (hoặc nút tương ứng có trong file) thì hệ thống kiểm tra cái gì.

    YÊU CẦU TRÌNH BÀY:
    - Sử dụng Bảng (Table) cho phần kịch bản: | Thành phần Form | Loại (Nút/Ô nhập/Thông tin) | Thao tác/Ý nghĩa |
    - Ngôn ngữ súc tích, bám sát thực tế "thấy gì viết nấy", không viết văn chương mơ hồ.
    """
        return self._call_ai_api(prompt)