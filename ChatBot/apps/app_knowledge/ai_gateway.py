import os
import tiktoken
from dotenv import load_dotenv
# Dùng ChatOllama thay vì Ollama để đồng bộ interface với Groq/Gemini
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

class AIGateway:
    def __init__(self, input_text=""):
        # 1. Tính toán token trước khi khởi tạo provider
        self.token_count = self._count_tokens(input_text)
        self.provider = self._choose_provider()
        print(f"--- 🤖 Khởi tạo AI Gateway | Provider: {self.provider} | Tokens: {self.token_count} ---")
    
    def _count_tokens(self, text):
        """Đếm token để quyết định dùng Local hay Cloud"""
        if not text: return 0
        encoding = tiktoken.get_encoding("cl100k_base") # Chuẩn cho GPT-4/Groq
        return len(encoding.encode(text))
    
    def _choose_provider(self):
        # Nếu token > 6000 (gần ngưỡng giới hạn của Groq free), ép dùng Ollama
        if self.token_count > 6000:
            return "Ollama"
        return os.getenv("DEFAULT_PROVIDER", "Ollama") # Mặc định dùng Ollama như anh muốn

    def get_chunks(self, text, chunk_size=4000):
        """Chia nhỏ dữ liệu nếu quá lớn"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=200
        )
        return text_splitter.split_text(text)

    def get_model(self):
        """
        Khởi tạo Chat Model dựa trên Provider đã chọn.
        Đã cập nhật langchain-ollama để tránh Deprecation Warning.
        """
        import os
        try:
            if self.provider == "Ollama":
                # Cập nhật: Sử dụng langchain-ollama thay cho langchain-community
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                    temperature=0,
                    num_thread=12, # Tăng số luồng CPU nếu không có GPU
                    num_ctx=4096  # Giới hạn context vừa đủ cho 1 sheet để chạy nhanh hơn
                )
                
            elif self.provider == "Groq":
                from langchain_groq import ChatGroq
                return ChatGroq(
                    temperature=0,
                    groq_api_key=os.getenv("GROQ_API_KEY"),
                    model_name=os.getenv("GROQ_MODEL")
                )
                
            elif self.provider == "Gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=os.getenv("GEMINI_MODEL"),
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                    temperature=0
                )
                
        except ImportError as e:
            print(f"❌ Thiếu thư viện cho {self.provider}: {str(e)}")
            print(f"💡 Thử chạy: pip install langchain-{self.provider.lower()}")
            return None
        except Exception as e:
            print(f"❌ Lỗi khởi tạo Model {self.provider}: {str(e)}")
            return None

    def process_ai_knowledge(self, prompt, use_ollama=False):
        """
        Xử lý gọi AI. 
        Nếu use_ollama=True: Ép dùng Ollama (dùng cho chạy hàng loạt).
        Nếu use_ollama=False: Ưu tiên Groq, tự động fallback sang Ollama nếu dính Rate Limit.
        """
        # Nếu được yêu cầu dùng Ollama ngay từ đầu (Bulk action)
        if use_ollama:
            original_provider = self.provider
            self.provider = "Ollama"
            model = self.get_model()
            try:
                print(f"🤖 Đang chạy chế độ hàng loạt: Sử dụng Ollama...")
                response = model.invoke(prompt)
                # Trả provider về trạng thái cũ sau khi xong để không ảnh hưởng các hàm khác
                self.provider = original_provider
                return response.content if hasattr(response, 'content') else ""
            except Exception as e:
                print(f"❌ Lỗi Ollama khi chạy hàng loạt: {str(e)}")
                self.provider = original_provider
                return None

        # Chế độ chạy đơn lẻ (Ưu tiên Groq)
        model = self.get_model()
        if not model: return None

        try:
            response = model.invoke(prompt)
            if not response or not hasattr(response, 'content'):
                return ""
            return response.content
        except Exception as e:
            error_msg = str(e)
            # Nếu gặp lỗi Rate Limit (429) và đang dùng Groq, tự động chuyển sang Ollama
            if "429" in error_msg and self.provider == "Groq":
                print(f"⚠️ Groq hết hạn mức (Rate Limit). Tự động chuyển sang Ollama chạy local...")
                self.provider = "Ollama"
                model = self.get_model() 
                if model:
                    try:
                        response = model.invoke(prompt)
                        return response.content if hasattr(response, 'content') else ""
                    except Exception as ollama_e:
                        print(f"❌ Ollama cũng gặp lỗi: {str(ollama_e)}")
            
            print(f"❌ Lỗi khi gọi AI ({self.provider}): {error_msg}")
            return None