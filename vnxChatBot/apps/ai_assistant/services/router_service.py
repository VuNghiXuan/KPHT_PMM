"""
Module: router_service.py
Path: apps/ai_assistant/services/router_service.py
Description:
    Điều phối định tuyến đa mô hình thông qua LiteLLM. 
    Tích hợp Circuit Breaker tự động chuyển đổi mượt mà từ Cloud (Gemini) 
    xuống Local Model (Ollama/Qwen) khi gặp lỗi quá tải (HTTP 429) hoặc sự cố mạng.
"""

import logging
from litellm import completion
from django.conf import settings

logger = logging.getLogger(__name__)

class MultiModelRouterService:
    """
    Quản lý luồng gọi LLM thông minh, tối ưu chi phí và đảm bảo tính sẵn sàng cao.
    """

    @staticmethod
    def route_and_generate(messages: list, complexity: str = "simple") -> tuple[str, str]:
        """
        Thực hiện định tuyến câu hỏi dựa trên mức độ phức tạp:
        - simple: Dùng mô hình nhanh/nhẹ (Gemini Flash).
        - complex: Xử lý sâu hoặc kích hoạt MoA pipeline.
        
        Trả về: (Nội dung phản hồi, Tên mô hình đã thực thi thực tế)
        """
        # Xác định mô hình Cloud ưu tiên
        primary_model = getattr(
            settings, 
            'AI_PRIMARY_MODEL', 
            'gemini/gemini-1.5-flash' if complexity == "simple" else 'gemini/gemini-1.5-pro'
        )
        
        # Mô hình dự phòng local theo chuẩn cấu hình hệ thống
        fallback_model = getattr(
            settings, 
            'AI_FALLBACK_MODEL', 
            'ollama/qwen2.5:7b'
        )
        ollama_base_url = getattr(settings, 'OLLAMA_API_BASE', 'http://localhost:11434')

        # Thử gọi Cloud Model trước
        try:
            logger.info(f"🚀 [Router] Đang gọi Cloud Model: {primary_model}")
            response = completion(
                model=primary_model,
                messages=messages,
                timeout=12
            )
            content = response['choices'][0]['message']['content']
            return content, primary_model

        except Exception as cloud_error:
            logger.warning(
                f"⚠️ [Circuit Breaker] Cloud API ({primary_model}) gặp lỗi hoặc quá tải: {str(cloud_error)}. "
                f"Đang kích hoạt Fallback xuống Local Model..."
            )
            
            # Kích hoạt Circuit Breaker chuyển hướng sang Local Model (Ollama)
            try:
                response = completion(
                    model=fallback_model,
                    messages=messages,
                    api_base=ollama_base_url,
                    timeout=30
                )
                content = response['choices'][0]['message']['content']
                logger.info(f"🛡️ [Circuit Breaker Success] Đã xử lý thành công bằng Local Model: {fallback_model}")
                return content, fallback_model

            except Exception as local_error:
                logger.error(f"❌ [Critical Error] Cả Cloud và Local Model đều không phản hồi: {str(local_error)}")
                raise RuntimeError("Hệ thống AI tạm thời gián đoạn toàn bộ, vui lòng thử lại sau.")