"""
Mục đích: Cung cấp Service trung tâm (LLMService) để kết nối với các LLM Provider.
Tác giả: Kiến trúc sư VnxChatBot
"""
import openai
import requests
from django.conf import settings
from google import genai

class LLMService:
    """
    Lớp xử lý LLM sử dụng Factory Pattern và Lazy Initialization.
    """
    @staticmethod
    def get_response(config, prompt: str) -> str:
        provider = config.provider.lower()
        if provider == 'groq': 
            return LLMService._call_groq(config, prompt)
        elif provider == 'gemini': 
            return LLMService._call_gemini(config, prompt)
        elif provider == 'ollama': 
            return LLMService._call_ollama(config, prompt)
        return "Provider không hợp lệ"

    @staticmethod
    def _call_groq(config, prompt: str) -> str:
        api_key = config.api_key or getattr(settings, 'GROQ_API_KEY', '')
        client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
        response = client.chat.completions.create(
            model=config.model_name or getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile'),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    @staticmethod
    def _call_gemini(config, prompt: str) -> str:
        api_key = config.api_key or getattr(settings, 'GOOGLE_API_KEY', '')
        model_name = config.model_name or getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model_name, contents=prompt)
        return response.text

    @staticmethod
    def _call_ollama(config, prompt: str) -> str:
        base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
        url = f"{base_url}/api/generate"
        payload = {
            "model": config.model_name or getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b'),
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get('response', '')
            return f"Lỗi kết nối Ollama: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"Không thể kết nối tới Ollama local: {str(e)}"

    @staticmethod
    def validate_provider_key(provider: str, api_key: str, model_name: str) -> bool:
        """
        Kiểm tra tính hợp lệ của API Key trước khi lưu để cải thiện UX.
        """
        try:
            if provider == 'gemini':
                client = genai.Client(api_key=api_key)
                client.models.generate_content(model=model_name, contents="ping")
                return True
            elif provider == 'groq':
                client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
                client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": "ping"}], max_tokens=1)
                return True
        except Exception:
            return False
        return True