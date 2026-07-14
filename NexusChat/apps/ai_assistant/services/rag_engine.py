import openai, google.generativeai as genai, requests
from django.conf import settings

class LLMService:
    @staticmethod
    def get_response(config, prompt):
        if config.provider == 'groq': return LLMService._call_groq(config, prompt)
        if config.provider == 'gemini': return LLMService._call_gemini(config, prompt)
        if config.provider == 'ollama': return LLMService._call_ollama(config, prompt)
        return "Provider không hợp lệ"

    @staticmethod
    def _call_groq(config, prompt):
        client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=config.api_key)
        response = client.chat.completions.create(model=config.model_name, messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    @staticmethod
    def _call_gemini(config, prompt):
        genai.configure(api_key=config.api_key)
        model = genai.GenerativeModel(config.model_name)
        return model.generate_content(prompt).text

    @staticmethod
    def _call_ollama(config, prompt):
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        response = requests.post(url, json={"model": config.model_name, "prompt": prompt, "stream": False})
        return response.json().get('response', '')