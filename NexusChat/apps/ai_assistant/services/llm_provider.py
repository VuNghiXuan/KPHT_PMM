import openai
import google.generativeai as genai
import requests
from django.conf import settings

class LLMService:
    """
    Service xử lý kết nối linh hoạt tới các LLM Provider.
    Lấy thông số từ settings.py (vốn đã load từ file .env).    
    """

    @staticmethod
    def get_response(config, prompt):
        """
        config: Object AIConfig (từ DB của bạn)
        prompt: Nội dung câu hỏi
        """
        provider = config.provider.lower()
        
        if provider == 'groq': 
            return LLMService._call_groq(config, prompt)
        elif provider == 'gemini': 
            return LLMService._call_gemini(config, prompt)
        elif provider == 'ollama': 
            return LLMService._call_ollama(config, prompt)
        else:
            return "Provider không được hỗ trợ hoặc chưa cấu hình đúng."

    @staticmethod
    def _call_groq(config, prompt):
        # Sử dụng API Key từ cấu hình người dùng (hoặc fallback về settings nếu cần)
        api_key = config.api_key or getattr(settings, 'GROQ_API_KEY', '')
        client = openai.OpenAI(
            base_url="https://api.groq.com/openai/v1", 
            api_key=api_key
        )
        response = client.chat.completions.create(
            model=config.model_name or getattr(settings, 'GROQ_MODEL', 'llama3-70b-8192'),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    @staticmethod
    def _call_gemini(config, prompt):
        api_key = config.api_key or getattr(settings, 'GOOGLE_API_KEY', '')
        genai.configure(api_key=api_key)
        
        # Chọn model từ config hoặc settings
        model_name = config.model_name or getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(prompt)
        return response.text

    @staticmethod
    def _call_ollama(config, prompt):
        # Ollama chạy local qua HTTP
        base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
        url = f"{base_url}/api/generate"
        
        payload = {
            "model": config.model_name or getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b'),
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json().get('response', '')
        return f"Lỗi kết nối Ollama: {response.status_code}"