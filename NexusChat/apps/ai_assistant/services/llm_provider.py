"""
Mục đích: Cung cấp Service trung tâm (LLMService) để kết nối với các LLM Provider (Gemini, Groq, Ollama).
Tác giả: AI Assistant
Module liên kết: apps.ai_assistant.models (AIConfig), django.conf (settings).
"""

import openai
import requests
from django.conf import settings
from google import genai  # Sử dụng thư viện mới theo cảnh báo của Google
from google.genai import types

class LLMService:
    """
    Lớp cung cấp dịch vụ LLM sử dụng Factory Pattern.
    Hỗ trợ chuyển đổi linh hoạt giữa các nhà cung cấp thông qua cấu hình từ Database (AIConfig) hoặc Settings.
    """

    @staticmethod
    def get_response(config, prompt: str) -> str:
        """
        Điều phối request tới đúng provider dựa trên cấu hình.

        Args:
            config: Object AIConfig chứa thông tin provider, api_key, model_name.
            prompt (str): Nội dung câu lệnh từ người dùng.

        Returns:
            str: Kết quả phản hồi từ LLM hoặc thông báo lỗi.
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
    def _call_groq(config, prompt: str) -> str:
        """Xử lý gọi API tới Groq sử dụng thư viện OpenAI client."""
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
    def _call_gemini(config, prompt: str) -> str:
        """
        Xử lý gọi API tới Google Gemini sử dụng thư viện google-genai mới.
        Sử dụng Lazy Initialization để tránh làm chậm server khi khởi động.
        """
        api_key = config.api_key or getattr(settings, 'GOOGLE_API_KEY', '')
        model_name = config.model_name or getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
        
        # Khởi tạo client tại thời điểm gọi (Lazy Loading) giúp giảm độ trễ startup của Django
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text

    @staticmethod
    def _call_ollama(config, prompt: str) -> str:
        """Xử lý gọi tới Local Ollama Instance."""
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