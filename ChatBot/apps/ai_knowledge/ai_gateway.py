import os
import json
import re
from dotenv import load_dotenv
# Dùng ChatOllama thay vì Ollama để đồng bộ interface với Groq/Gemini
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

class AIGateway:
    def __init__(self, token_count=0):
        self.token_count = token_count
        self.provider = self._choose_provider()
        print(f"--- 🤖 Khởi tạo AI Gateway | Provider: {self.provider} | Tokens: {self.token_count} ---")
        
    def _choose_provider(self):
        # Ưu tiên Ollama nếu dữ liệu quá lớn (tiết kiệm chi phí/vượt giới hạn)
        if self.token_count > 8000:
            return "Ollama"
        return os.getenv("DEFAULT_PROVIDER", "Groq")

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

    def process_ai_knowledge(self, prompt):
        # Thử provider ưu tiên trước
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
                model = self.get_model() # Khởi tạo lại model Ollama
                if model:
                    try:
                        response = model.invoke(prompt)
                        return response.content if hasattr(response, 'content') else ""
                    except Exception as ollama_e:
                        print(f"❌ Ollama cũng gặp lỗi: {str(ollama_e)}")
            
            print(f"❌ Lỗi khi gọi AI ({self.provider}): {error_msg}")
            return None