"""
Mục đích: Cung cấp LLM với cơ chế fallback thông minh (Hierarchical Config).
Tác giả: Kiến trúc sư VnxChatBot
"""
from django.conf import settings
from apps.ai_assistant.models import GroupAIProvider
from .llm_provider import LLMService

class AIFactory:
    @staticmethod
    def get_service_for_group(group, prompt: str) -> str:
        """
        Lấy cấu hình AI cho nhóm.
        Tại sao (Why): Ưu tiên key riêng do User cấp (GroupAIProvider) -> Rơi về Default Settings (Free Tier).
        """
        class DefaultConfig:
            provider = getattr(settings, 'DEFAULT_PROVIDER', 'Ollama').lower()
            api_key = getattr(settings, f'{provider.upper()}_API_KEY', '') 
            model_name = getattr(settings, f'{provider.upper()}_MODEL', 'qwen2.5:7b')

        try:
            config = group.ai_config
            return LLMService.get_response(config, prompt)
        except GroupAIProvider.DoesNotExist:
            return LLMService.get_response(DefaultConfig, prompt)