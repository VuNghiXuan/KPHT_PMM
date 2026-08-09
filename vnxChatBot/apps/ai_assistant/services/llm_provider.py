"""
Mục đích: Cung cấp Service trung tâm (LLMService) để kết nối với các LLM Provider.
Đặc điểm: Hỗ trợ Backward Compatibility (ai_model <-> model_name), 
         Safety Fallback (Settings), và cấu trúc lỗi rõ ràng.
Tác giả: Kiến trúc sư VnxChatBot (Phiên bản 2.0)
"""
import openai
import requests
import logging
from django.conf import settings
from google import genai

logger = logging.getLogger(__name__)

class LLMService:
    """
    Lớp xử lý LLM sử dụng Factory Pattern và Lazy Initialization.
    Cung cấp cơ chế fallback an toàn cho các cấu hình cũ và mới.
    """

    @staticmethod
    def _get_config_attr(config, keys: list, default_setting: str, default_val: str) -> str:
        """
        Helper method: Tìm kiếm giá trị theo thứ tự ưu tiên:
        1. Các khóa trong config object (đã check hasattr).
        2. Biến môi trường/settings mặc định.
        3. Giá trị fallback cứng.
        """
        for key in keys:
            val = getattr(config, key, None)
            if val:
                return val
        return getattr(settings, default_setting, default_val)

    @staticmethod
    def get_response(config, prompt: str) -> str:
        provider = getattr(config, 'provider', 'gemini').lower()
        
        try:
            if provider == 'groq': 
                return LLMService._call_groq(config, prompt)
            elif provider == 'gemini': 
                return LLMService._call_gemini(config, prompt)
            elif provider == 'ollama': 
                return LLMService._call_ollama(config, prompt)
            return f"Error: Provider '{provider}' chưa được hỗ trợ."
        except Exception as e:
            logger.error(f"LLMService Error [{provider}]: {str(e)}")
            return f"Hệ thống AI đang gặp lỗi kết nối: {str(e)}"

    @staticmethod
    def _call_groq(config, prompt: str) -> str:
        api_key = LLMService._get_config_attr(config, ['api_key', 'custom_api_key'], 'GROQ_API_KEY', '')
        model = LLMService._get_config_attr(config, ['model_name', 'ai_model'], 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        
        client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    @staticmethod
    def _call_gemini(config, prompt: str) -> str:
        api_key = LLMService._get_config_attr(config, ['api_key', 'custom_api_key'], 'GOOGLE_API_KEY', '')
        model = LLMService._get_config_attr(config, ['model_name', 'ai_model'], 'GEMINI_MODEL', 'gemini-2.0-flash')
        
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text

    @staticmethod
    def _call_ollama(config, prompt: str) -> str:
        base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
        url = f"{base_url}/api/generate"
        model = LLMService._get_config_attr(config, ['model_name', 'ai_model'], 'OLLAMA_MODEL', 'qwen2.5:7b')
        
        payload = {"model": model, "prompt": prompt, "stream": False}
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json().get('response', '')
        raise Exception(f"Ollama trả về status {response.status_code}")

    @staticmethod
    def validate_provider_key(provider: str, api_key: str, model_name: str) -> bool:
        """
        Kiểm tra tính hợp lệ của API Key (Health check).
        """
        try:
            if provider == 'gemini':
                client = genai.Client(api_key=api_key)
                client.models.generate_content(model=model_name, contents="ping")
            elif provider == 'groq':
                client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
                client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": "ping"}], max_tokens=1)
            return True
        except Exception:
            return False