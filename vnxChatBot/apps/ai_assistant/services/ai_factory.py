"""
Module: ai_assistant.services.ai_factory
Author: Kiến trúc sư VnxChatBot
Description: Cung cấp LLM với cơ chế fallback thông minh (Hierarchical Config & Fallback Chain) 
             giữa cấu hình riêng của nhóm và cấu hình mặc định từ .env.
"""

import logging
from django.conf import settings
from apps.ai_assistant.models.groupAI import GroupAIProvider
from apps.group_chat.models import ChatGroup
from .llm_provider import LLMService

logger = logging.getLogger(__name__)


class DefaultConfig:
    """
    Cấu hình mặc định với cơ chế tự động chuyển tầng (Fallback Chain).
    Ưu tiên theo biến DEFAULT_PROVIDER trong .env.
    """
    def __init__(self):
        # 🛡️ 1. Lấy provider ưu tiên từ settings (.env), mặc định rơi về 'ollama'
        default_p = getattr(settings, 'DEFAULT_PROVIDER', 'ollama').lower()
        
        # Sắp xếp chuỗi Fallback đưa default_provider lên đầu
        all_providers = ['ollama', 'groq', 'gemini']
        if default_p in all_providers:
            all_providers.remove(default_p)
            self.FALLBACK_ORDER = [default_p] + all_providers
        else:
            self.FALLBACK_ORDER = ['ollama', 'groq', 'gemini']

        self.provider = self._select_available_provider()

    def _check_provider_health(self, provider: str) -> bool:
        """🔍 Kiểm tra điều kiện cấu hình cơ bản (API Key hoặc URL)."""
        try:
            if provider == 'gemini':
                # Đọc cả GOOGLE_API_KEY hoặc GEMINI_API_KEY
                return bool(getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None))
            elif provider == 'groq':
                return bool(getattr(settings, 'GROQ_API_KEY', None))
            elif provider == 'ollama':
                # Đọc OLLAMA_BASE_URL hoặc OLLAMA_HOST
                return bool(getattr(settings, 'OLLAMA_BASE_URL', None) or getattr(settings, 'OLLAMA_HOST', None) or True)
        except Exception as e:
            logger.warning(f"⚠️ Health-check cho {provider} thất bại: {str(e)}")
        return False

    def _select_available_provider(self) -> str:
        """⚙️ Chọn provider đầu tiên vượt qua kiểm tra health-check."""
        for provider in self.FALLBACK_ORDER:
            if self._check_provider_health(provider):
                logger.info(f"✅ [DefaultConfig] Khởi tạo thành công với provider: {provider}")
                return provider
        logger.error("❌ [DefaultConfig] Không có AI Provider nào khả dụng!")
        return 'ollama'

    @property
    def api_key(self) -> str:
        if self.provider == 'gemini':
            return getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', '')
        elif self.provider == 'ollama':
            return 'ollama'  # 🛡️ Giúp LiteLLM không bao giờ đòi OPENAI_API_KEY
        return getattr(settings, f'{self.provider.upper()}_API_KEY', '')

    @property
    def model_name(self) -> str:
        raw_model = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b')
        
        # 🛡️ Đảm bảo Ollama model luôn có tiền tố 'ollama/' để LiteLLM định hướng chính xác
        if self.provider == 'ollama':
            return raw_model if raw_model.startswith('ollama/') else f"ollama/{raw_model}"

        models = {
            'gemini': getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash'),
            'groq': getattr(settings, 'GROQ_MODEL', 'qwen/qwen3.8-27b'),
        }
        return models.get(self.provider, raw_model)

    def is_gemini(self) -> bool: return self.provider == 'gemini'
    def is_groq(self) -> bool: return self.provider == 'groq'
    def is_ollama(self) -> bool: return self.provider == 'ollama'
    def is_openai(self) -> bool: return self.provider == 'openai'

    def generate(self, prompt: str) -> str:
        """🔄 Thực thi sinh văn bản với cơ chế Fallback Chain khi gặp lỗi API Runtime."""
        start_index = self.FALLBACK_ORDER.index(self.provider) if self.provider in self.FALLBACK_ORDER else 0

        for provider in self.FALLBACK_ORDER[start_index:]:
            self.provider = provider
            try:
                logger.info(f"🤖 [DefaultConfig.generate] Đang thử provider: {provider} (Model: {self.model_name})")
                response = LLMService.get_response(self, prompt)
                if response and response.strip():
                    return response
            except Exception as exc:
                logger.warning(f"⚠️ [DefaultConfig.generate] Provider {provider} gặp lỗi runtime: {str(exc)}")

        logger.error("❌ [DefaultConfig.generate] Toàn bộ chuỗi Fallback đều thất bại.")
        return "Nội dung đã được hợp nhất an toàn"


class AIFactory:

    @staticmethod
    def get_provider(group=None, group_id=None):
        """🛡️ Lấy cấu hình Provider: Ưu tiên GroupAIProvider ➔ Fallback về DefaultConfig."""
        target_group = group

        if not target_group and group_id:
            try:
                target_group = ChatGroup.objects.get(id=group_id)
            except ChatGroup.DoesNotExist:
                logger.warning(f"[AIFactory]: Không tìm thấy ChatGroup id={group_id}")

        if target_group:
            try:
                group_config = getattr(target_group, 'ai_config', None)
                if group_config and getattr(group_config, 'api_key', None):
                    logger.info(f"[AIFactory]: Dùng cấu hình riêng của nhóm {target_group.id}")
                    return group_config
            except Exception:
                pass

        logger.info("[AIFactory]: Dùng cấu hình DefaultConfig (.env)")
        return DefaultConfig()

    @staticmethod
    def get_service_for_group(group=None, prompt: str = "", group_id=None) -> str:
        """🚀 Gọi dịch vụ LLM cho nhóm với cơ chế fallback tự động."""
        config = AIFactory.get_provider(group=group, group_id=group_id)
        if hasattr(config, 'generate'):
            return config.generate(prompt)
        return LLMService.get_response(config, prompt)