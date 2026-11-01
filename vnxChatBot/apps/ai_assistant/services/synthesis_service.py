# -*- coding: utf-8 -*-
"""
Module: apps.ai_assistant.services.synthesis_service
Mục đích: Chứa logic gọi LLM qua LiteLLM để tổng hợp tri thức khi xảy ra xung đột (Conflict Resolution & Synthesis).
"""

import logging
from apps.ai_assistant.utils import get_llm_client

logger = logging.getLogger(__name__)

def synthesize_knowledge_conflict(new_content: str, existing_contents: list, user_prompt: str) -> str:
    """
    Sử dụng LLM (Gemini 1.5 Flash qua LiteLLM) để trộn nội dung cũ và mới 
    dựa trên hướng dẫn bổ sung (prompt) của quản trị viên.
    
    Args:
        new_content (str): Nội dung mới đang chờ xử lý (Pending content).
        existing_contents (list): Danh sách nội dung cũ đã được phê duyệt có liên quan.
        user_prompt (str): Hướng dẫn bổ sung từ quản trị viên trên giao diện.
        
    Returns:
        str: Nội dung đã được biên soạn lại theo định dạng Markdown sạch sẽ.
    """
    client = get_llm_client()
    
    # Định dạng rõ ràng dữ liệu đầu vào cho Prompt để AI dễ dàng đối chiếu
    formatted_existing = "\n---\n".join(existing_contents) if existing_contents else "Không có dữ liệu cũ liên quan trực tiếp."
    
    prompt = f"""
    Bạn là chuyên gia tổng hợp tri thức doanh nghiệp. Nhiệm vụ của bạn là biên soạn lại một phiên bản tri thức chính thức duy nhất, đảm bảo tính nhất quán, logic và cập nhật mốc thời gian mới nhất.
    
    [DỮ LIỆU CŨ (Approved)]:
    {formatted_existing}
    
    [DỮ LIỆU MỚI (Pending)]:
    {new_content}
    
    [HƯỚNG DẪN BỔ SUNG TỪ QUẢN TRỊ VIÊN]:
    {user_prompt if user_prompt else "Không có hướng dẫn bổ sung, hãy tự động cân nhắc thông tin mới nhất để ghi đè hoặc hợp nhất hợp lý."}
    
    Yêu cầu đầu ra:
    1. Trả về nội dung hoàn chỉnh đã được tổng hợp.
    2. Định dạng đầu ra hoàn toàn bằng Markdown sạch sẽ, súc tích.
    3. Không kèm theo các lời chào hay giải thích dài dòng ngoài nội dung chính.
    """
    
    try:
        response = client.chat.completions.create(
            model="gemini-1.5-flash", # 🚀 Ưu tiên tốc độ và tiết kiệm token cho tác vụ nền
            messages=[
                {"role": "system", "content": "Bạn là AI chuyên gia tổng hợp tri thức chuẩn hóa doanh nghiệp."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 # Giảm độ sáng tạo để tập trung vào tính chính xác của dữ liệu
        )
        
        synthesized_text = response.choices[0].message.content.strip()
        logger.info("✨ [AI Synthesis]: Tổng hợp mâu thuẫn tri thức thành công.")
        return synthesized_text
        
    except Exception as e:
        logger.error(f"❌ [AI Synthesis Error]: Lỗi khi gọi LiteLLM: {str(e)}")
        # Phương án dự phòng (Fallback): Trả về nội dung mới kết hợp cảnh báo nhỏ
        return f"{new_content}\n\n> ⚠️ *Lưu ý: Hệ thống không thể tự động tổng hợp do lỗi kết nối AI. Vui lòng kiểm tra lại thủ công.*"