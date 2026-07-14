from celery import shared_task
from .services.llm_provider import LLMService
from .services.rag_engine import RAGEngine
from .models import AIConfig

@shared_task
def process_ai_chat_task(user_id, group_id, prompt, use_rag):
    # 1. Truy vấn RAG nếu cần
    context = RAGEngine.get_context(group_id, prompt) if use_rag else ""
    
    # 2. Xây dựng prompt
    full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
    
    # 3. Lấy cấu hình và gọi AI
    config = AIConfig.objects.filter(owner_id=user_id, is_default=True).first()
    if not config: return "Vui lòng cấu hình API Key!"
    
    response = LLMService.get_response(config, full_prompt)
    
    # 4. Gửi kết quả về UI (Dùng Django Channels ở đây)
    # channel_layer = get_channel_layer()
    # async_to_sync(channel_layer.group_send)(f"chat_{group_id}", {"type": "chat_message", "message": response})
    
    return response