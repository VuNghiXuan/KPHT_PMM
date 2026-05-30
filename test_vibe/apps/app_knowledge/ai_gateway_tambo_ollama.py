import os
import tiktoken
import subprocess
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

class AIGateway:
    def __init__(self, config_obj, input_text=""):
        self.config = config_obj  # Lấy trực tiếp từ DB
        self.input_text = input_text
        self.token_count = self._count_tokens(input_text)
        self.has_gpu = self._check_gpu()
        self.provider = self._choose_provider()
        
        print(f"--- 🤖 AI Gateway | {self.provider} | Tokens: {self.token_count} | GPU: {self.has_gpu} ---")

    def _check_gpu(self):
        try:
            subprocess.check_output('nvidia-smi', stderr=subprocess.STDOUT)
            return True
        except: return False

    def _count_tokens(self, text):
        if not text: return 0
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    def _choose_provider(self):
        if self.config.provider_strategy != 'AUTO':
            return self.config.provider_strategy
        # Nếu vượt ngưỡng hoặc không có API Key đám mây thì ép về Ollama
        if self.token_count > self.config.max_token_threshold:
            return "Ollama"
        return os.getenv("DEFAULT_PROVIDER", "Groq")

    def get_model(self):
        p = self.provider
        # Ưu tiên: Model trong DB -> Model trong .env -> Model mặc định của hệ thống
        model_name = self.config.model_name or os.getenv(f"{p.upper()}_MODEL")

        try:
            if p == "Ollama":
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=model_name or "qwen2.5:7b",
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                    temperature=self.config.temperature,
                    num_ctx=self.config.num_ctx,
                    num_gpu=self.config.num_gpu_layers if self.has_gpu else 0,
                    num_thread=12 if not self.has_gpu else None
                )

            elif p == "Groq":
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model_name=model_name or "llama-3.1-70b-versatile",
                    temperature=self.config.temperature
                )

            elif p == "Gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model_name or "gemini-1.5-flash",
                    temperature=self.config.temperature
                )
        except Exception as e:
            print(f"❌ Lỗi khởi tạo {p}: {e}")
            return None

    def run_process(self):
        """
        Thực thi chính: Tự động điều tiết giữa chạy thẳng và Chunking.
        Đã fix lỗi Invalid format specifier bằng cách dùng Message trực tiếp.
        """
        # 1. Kiểm tra ngưỡng Token để quyết định có Chunking hay không
        if self.token_count > self.config.max_token_threshold and self.provider == "Ollama":
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=500)
            chunks = splitter.split_text(self.input_text)
            return self._summarize_chunks(chunks)

        # 2. Chạy trực tiếp (Sử dụng cấu trúc Message để né lỗi format ngoặc nhọn)
        model = self.get_model()
        if not model:
            return "❌ Lỗi: Không thể khởi tạo AI Model."

        messages = [
            SystemMessage(content=self.config.system_prompt),
            HumanMessage(content=self.input_text)
        ]
        
        try:
            response = model.invoke(messages)
            return response.content
        except Exception as e:
            return f"❌ AI Error: {str(e)}"

    def _summarize_chunks(self, chunks):
        """Xử lý đệ quy cho các bộ Metadata Excel quá lớn."""
        print(f"⚙️ Chunking Mode: {len(chunks)} phần...")
        model = self.get_model()
        if not model:
            return "❌ Lỗi: Không thể khởi tạo AI Model cho Chunking."
        
        # 1. Tóm tắt từng phần (Map)
        summaries = []
        for i, chunk in enumerate(chunks):
            print(f"   🔹 Đang xử lý phần {i+1}/{len(chunks)}...")
            chunk_messages = [
                SystemMessage(content=f"{self.config.system_prompt}\n(Lưu ý: Đây là phần {i+1} của dữ liệu lớn)"),
                HumanMessage(content=chunk)
            ]
            res = model.invoke(chunk_messages)
            summaries.append(res.content)

        # 2. Hợp nhất bản cuối (Reduce)
        print(f"   📝 Đang tổng hợp kết quả cuối cùng...")
        final_messages = [
            SystemMessage(content=self.config.system_prompt),
            HumanMessage(content="Dưới đây là các phần phân tích rời rạc. Hãy tổng hợp chúng thành một bản hướng dẫn nghiệp vụ hoàn chỉnh, logic và không lặp lại:\n\n" + "\n\n".join(summaries))
        ]
        
        try:
            final_response = model.invoke(final_messages)
            return final_response.content
        except Exception as e:
            return f"❌ Lỗi tổng hợp: {str(e)}"