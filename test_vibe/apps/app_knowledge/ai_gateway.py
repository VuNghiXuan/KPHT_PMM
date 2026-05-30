import os
import time
import logging
import tiktoken
import subprocess
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)
load_dotenv()

class AIGateway:
    def __init__(self, config_obj, input_text=""):
        self.config = config_obj  # Cấu hình từ DB (DataType)
        self.input_text = input_text
        self.token_count = self._count_tokens(input_text)
        self.provider = self.config.provider_strategy if self.config.provider_strategy != 'AUTO' else "Groq"
        
        # Quản lý danh sách API Keys phục vụ cho cơ chế xoay vòng (Rotation)
        self.api_keys = self._load_api_keys(self.provider)
        self.current_key_index = 0

    def _count_tokens(self, text):
        if not text: return 0
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            return len(text) // 4  # Fallback tính thô nếu lỗi thư viện

    def _load_api_keys(self, provider):
        """
        Nạp danh sách API Key từ .env. 
        Định dạng trong .env: 
        GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
        GEMINI_API_KEYS=AIzaSyKey1,AIzaSyKey2
        """
        raw_keys = os.getenv(f"{provider.upper()}_API_KEYS", "")
        if raw_keys:
            return [k.strip() for k in raw_keys.split(",") if k.strip()]
        
        # Fallback về biến đơn lẻ truyền thống nếu không cấu hình chuỗi list
        single_key = os.getenv(f"{provider.upper()}_API_KEY", "")
        return [single_key] if single_key else []

    def _get_current_key(self):
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_index]

    def _rotate_key(self):
        """Chuyển sang API Key tiếp theo trong danh sách dự phòng"""
        if len(self.api_keys) <= 1:
            return False
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"🔄 [GATEWAY] Đang xoay vòng sang API Key dự phòng thứ {self.current_key_index + 1}...")
        return True

    def get_model(self, current_key):
        p = self.provider
        model_name = self.config.model_name or os.getenv(f"{p.upper()}_MODEL")

        try:
            if p == "Groq":
                from langchain_groq import ChatGroq
                return ChatGroq(
                    groq_api_key=current_key,
                    model_name=model_name or "llama-3.1-70b-versatile",
                    temperature=self.config.temperature
                )

            elif p == "Gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    google_api_key=current_key,
                    model=model_name or "gemini-1.5-flash",
                    temperature=self.config.temperature
                )
                
            elif p == "Ollama":
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=model_name or "qwen2.5:7b",
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                    temperature=self.config.temperature,
                    num_ctx=self.config.num_ctx
                )
        except Exception as e:
            print(f"❌ Lỗi khởi tạo Model {p}: {e}")
            return None

    def run_process(self):
        """
        Luồng thực thi chính: Tự động xử lý bẫy Rate Limit và Token Quota Exceeded.
        """
        # Nếu Token vượt quá ngưỡng chịu đựng của Cloud Free (ví dụ > 30k token) -> Ép về Ollama xử lý
        if self.token_count > self.config.max_token_threshold and self.provider != "Ollama":
            print(f"⚠️ Dữ liệu quá lớn ({self.token_count} tokens). Ép luồng về Local Ollama để tránh sập Cloud.")
            self.provider = "Ollama"

        max_retries = max(len(self.api_keys) * 2, 3) # Số lần thử lại tối đa dựa trên lượng Key
        
        for attempt in range(max_retries):
            current_key = self._get_current_key()
            
            if self.provider != "Ollama" and not current_key:
                raise Exception(f"Cạn kiệt hoặc thiếu API Key cho nhà cung cấp {self.provider}")

            model = self.get_model(current_key)
            if not model:
                return "❌ Lỗi: Không thể cấu hình instance cho AI Model."

            messages = [
                SystemMessage(content=self.config.system_prompt),
                HumanMessage(content=self.input_text)
            ]
            
            try:
                # Thực thi gọi Cloud/Ollama
                response = model.invoke(messages)
                return response.content

            except Exception as e:
                error_msg = str(e).lower()
                
                # BẪY LỖI 1: Rate Limit hoặc Quota trong ngày bị hết (429, rate_limit_exceeded, quota)
                if "429" in error_msg or "rate_limit" in error_msg or "quota" in error_msg or "limit exceeded" in error_msg:
                    print(f"⚠️ [RATE LIMIT] Dính giới hạn băng thông Cloud tại lượt thử {attempt + 1}.")
                    
                    # Thử xoay vòng sang Key tài khoản khác xem còn lượt không
                    if self._rotate_key():
                        time.sleep(1) # Nghỉ 1s trước khi nạp key mới
                        continue
                    else:
                        # Nếu không có key nào khác để xoay, bắt buộc phải ngủ đông chờ hồi phục (Cool down)
                        print("💤 Toàn bộ API Key đã cạn kiệt. Hệ thống sẽ ngủ đông 30 giây để hồi Quota...")
                        time.sleep(30)
                        continue
                
                # BẪY LỖI 2: Quá giới hạn độ dài Context của gói Free (413 hoặc context_length)
                elif "413" in error_msg or "context" in error_msg:
                    print("🚨 [CONTEXT EXCEEDED] Dữ liệu sheet này quá nặng so với gói Cloud Free. Đẩy về Ollama gánh!")
                    self.provider = "Ollama"
                    continue
                
                # Các lỗi hệ thống hoặc rớt mạng khác
                else:
                    print(f"❌ Lỗi không xác định từ AI Provider: {e}")
                    # Xoay key thử vận may phát cuối
                    if not self._rotate_key():
                        raise e # Nếu có 1 key duy nhất thì ném lỗi ra ngoài luôn

        # Nếu đi hết vòng lặp mà vẫn không xong -> Trả lỗi nghiêm trọng để dừng Batch
        raise Exception("STOP_BATCH: Tất cả các đầu API Cloud đều đã hết hạn mức (Quota) hoặc bị khóa tạm thời.")