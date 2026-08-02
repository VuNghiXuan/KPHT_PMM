"""
Mục đích: Cung cấp LLM với cơ chế fallback thông minh (Hierarchical Config) giữa cấu hình riêng của nhóm và cấu hình mặc định từ .env.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: django.conf, apps.ai_assistant.models, apps.group_chat.models, apps.ai_assistant.services.llm_provider
"""
import logging
from django.conf import settings
from apps.ai_assistant.models import GroupAIProvider
from apps.group_chat.models import ChatGroup
from .llm_provider import LLMService

# Khởi tạo logger để ghi log vào file debug_vnx.log và console
logger = logging.getLogger(__name__)

class AIFactory:
    @staticmethod
    def get_provider(group=None, group_id=None):
        """
        Lấy cấu hình Provider phù hợp theo thứ tự ưu tiên (Hierarchical Config):
        1. Ưu tiên cấu hình riêng của nhóm (GroupAIProvider) nếu nhóm đã thiết lập và có API Key.
        2. Fallback về cấu hình mặc định toàn cục từ tệp .env (thông qua settings).
        
        Tại sao (Why): Hỗ trợ cả tham số 'group' (object) lẫn 'group_id' (int/str/uuid) 
        để tránh lỗi TypeError khi gọi nhầm từ khóa từ các service hoặc consumer khác nhau.
        """
        target_group = group
        
        logger.info(f"[AIFactory.get_provider]: Đang phân giải cấu hình AI cho group={group}, group_id={group_id}")
        
        # Nếu truyền vào group_id thay vì object group, tiến hành truy vấn ngược lại
        if not target_group and group_id:
            try:
                target_group = ChatGroup.objects.get(id=group_id)
                logger.info(f"[AIFactory.get_provider]: Tìm thấy ChatGroup từ group_id={group_id} -> Tên nhóm: {target_group.name}")
            except ChatGroup.DoesNotExist:
                logger.warning(f"[AIFactory.get_provider]: Không tìm thấy ChatGroup với id={group_id}")
                target_group = None

        # 1. Thử lấy cấu hình riêng của nhóm nếu tìm thấy target_group hợp lệ
        # 1. Thử lấy cấu hình riêng của nhóm nếu tìm thấy target_group hợp lệ
        if target_group:
            try:
                # Sử dụng getattr hoặc bọc try-except an toàn tuyệt đối
                group_config = getattr(target_group, 'ai_config', None)
                if group_config and getattr(group_config, 'api_key', None):
                    logger.info(f"[AIFactory.get_provider]: Sử dụng cấu hình RIÊNG của nhóm {target_group.name} (Provider: {group_config.provider})")
                    return group_config
            except Exception:
                logger.info(f"[AIFactory.get_provider]: Nhóm {target_group.name} chưa cấu hình AI riêng, chuyển sang fallback.")
                pass

        # 2. Nếu nhóm không có cấu hình riêng, sử dụng cấu hình mặc định toàn cục từ hệ thống (.env)
        logger.info(f"[AIFactory.get_provider]: Đang sử dụng cấu hình MẶC ĐỊNH toàn cục từ .env")
        
        class DefaultConfig:
            provider = getattr(settings, 'DEFAULT_PROVIDER', 'groq').lower()
            
            @property
            def api_key(self):
                key = getattr(settings, f'{self.provider.upper()}_API_KEY', '')
                logger.info(f"[DefaultConfig]: Lấy API Key cho provider '{self.provider}' (Độ dài key: {len(key)})")
                return key

            @property
            def model_name(self):
                if self.provider == 'gemini':
                    model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
                elif self.provider == 'groq':
                    model = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
                elif self.provider == 'ollama':
                    model = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b')
                else:
                    model = 'llama-3.3-70b-versatile'
                logger.info(f"[DefaultConfig]: Model được chọn cho {self.provider}: {model}")
                return model

            def is_gemini(self):
                return self.provider == 'gemini'

            def is_groq(self):
                return self.provider == 'groq'

            def is_ollama(self):
                return self.provider == 'ollama'

            def is_openai(self):
                return self.provider == 'openai'

            def generate(self, prompt: str) -> str:
                """
                Triển khai phương thức generate trên DefaultConfig để tương thích trực tiếp 
                với các service gọi hàm trực tiếp trên đối tượng config.
                """
                logger.info(f"[DefaultConfig.generate]: Thực thi sinh văn bản với prompt dài {len(prompt)} ký tự.")
                return LLMService.get_response(self, prompt)

        return DefaultConfig()

    @staticmethod
    def get_service_for_group(group=None, prompt: str = "", group_id=None) -> str:
        """
        Thực hiện gọi LLM Service cho nhóm thông qua cấu hình đã được phân giải (Group-level hoặc Global .env).
        Hỗ trợ nhận cả group, group_id hoặc prompt một cách linh hoạt.
        """
        logger.info(f"[AIFactory.get_service_for_group]: Bắt đầu tiến trình gọi LLM service.")
        config = AIFactory.get_provider(group=group, group_id=group_id)
        return LLMService.get_response(config, prompt)