# app_ai_core/services.py
import tiktoken
import logging
from django.db import transaction
from .models import AITokenLog, AIPromptConfig

logger = logging.getLogger(__name__)

def chunk_content_purify(content_text, chunk_size=10000, model_encoding="cl100k_base"):
    """
    Giai đoạn 1: Chunking (Cắt bánh)
    Cắt nhỏ chuỗi văn bản khổng lồ dựa trên số lượng Token thực tế.
    """
    try:
        encoding = tiktoken.get_encoding(model_encoding)
    except Exception:
        encoding = None

    lines = content_text.split('\n')
    chunks = []
    current_chunk = []
    current_tokens = 0

    for line in lines:
        line_tokens = len(encoding.encode(line)) if encoding else len(line) // 4
        
        if current_tokens + line_tokens > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_tokens = line_tokens
        else:
            current_chunk.append(line)
            current_tokens += line_tokens

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def get_available_key_or_fallback(provider, estimated_tokens=15000):
    """
    Bộ lọc rổ Key: Tìm kiếm Key còn hạn mức xanh và tối ưu tải (Load Balancing).
    Sắp xếp lấy con có số lượt gọi trong ngày ít nhất lên đầu.
    """
    # SỬA LỖI: Thay hàm lỗi bằng order_by tiêu chuẩn của Django ORM
    active_keys = AITokenLog.objects.filter(
        provider=provider, 
        is_active=True
    ).order_by('requests_today')
    
    for key in active_keys:
        if key.has_enough_quota(estimated_tokens):
            return key
    return None


def execute_map_reduce_miner(excel_raw_text, module_code="SYSTEM", function_code="GLOBAL"):
    """
    Giai đoạn 2 & 3: Map-Reduce kết hợp Token Auditing toàn diện
    """
    # 1. Khởi tạo cấu hình và ước lượng Token tổng
    config = AIPromptConfig.objects.filter(module_code=module_code, function_code=function_code, is_active=True).first()
    if not config:
        config = AIPromptConfig.objects.get(is_default=True)
        
    chunks = chunk_content_purify(excel_raw_text, chunk_size=10000)
    total_chunks = len(chunks)
    estimated_total_tokens = total_chunks * 12000 
    
    logger.info(f"🚀 Bắt đầu xử lý Map-Reduce: Chia thành {total_chunks} phân đoạn.")
    
    # 2. CHỐT CHẶN THÔNG MINH (Token Auditing Quota)
    strategy = config.provider_strategy
    map_summaries = []
    
    # Chuẩn hóa Provider mục tiêu
    chosen_provider = 'GEMINI'
    if strategy == 'GROQ':
        chosen_provider = 'GROQ'
        
    if strategy in ['AUTO', 'GEMINI', 'GROQ']:
        # Kiểm tra tổng năng lực rổ Key trước khi phát lệnh càn quét
        available_key = get_available_key_or_fallback(chosen_provider, estimated_tokens=estimated_total_tokens)
        
        if not available_key:
            logger.warning("🚨 [QUOTA CRITICAL] Rổ Key Cloud Free đã kiệt quệ! Kích hoạt Smart Fallback về Local Ollama.")
            strategy = 'OLLAMA'
            
    # 3. GIAI ĐOẠN 2: MAP (Xử lý thô từng phân đoạn)
    if strategy == 'OLLAMA':
        for index, chunk in enumerate(chunks):
            logger.info(f"🤖 [OLLAMA LOCAL] Đang xử lý phân đoạn {index + 1}/{total_chunks}...")
            summary = call_local_ollama_engine(
                prompt_text=chunk, 
                system_prompt="Tóm tắt cô đọng logic, công thức tiệm vàng trong đoạn dữ liệu này, loại bỏ nhiễu.",
                model_name=config.model_name or "qwen2.5:7b"
            )
            map_summaries.append(summary)
            
    else:
        # Lấy danh sách toàn bộ Key khả dụng của provider này để làm rổ xoay tua chủ động
        pool_keys = list(AITokenLog.objects.filter(provider=chosen_provider, is_active=True).order_by('requests_today'))
        
        for index, chunk in enumerate(chunks):
            if not pool_keys:
                logger.error(f"💥 Không còn key nào khả dụng trong rổ. Đẩy phân đoạn {index + 1} về Ollama cứu hộ.")
                summary = call_local_ollama_engine(chunk, "Tóm tắt cô đọng...", "qwen2.5:7b")
                map_summaries.append(summary)
                continue
                
            # Xoay tua chủ động theo chỉ số Index để tránh trùng lặp Key khi DB chưa kịp lưu
            key_obj = pool_keys[index % len(pool_keys)]
            
            if not key_obj.has_enough_quota(estimated_tokens=12000):
                # Nếu con key được xoay tua trúng lại hết hạn mức, quét tìm con khác thay thế
                key_obj = get_available_key_or_fallback(chosen_provider, estimated_tokens=12000)
                
            if not key_obj:
                logger.error(f"💥 Đứt gãy luồng Cloud tại phân đoạn {index + 1}. Đẩy về Ollama cứu hộ.")
                summary = call_local_ollama_engine(chunk, "Tóm tắt cô đọng...", "qwen2.5:7b")
            else:
                logger.info(f"☁️ [CLOUD API] Phân đoạn {index + 1}/{total_chunks} đang dùng Key: {key_obj.key_name}")
                
                # Thực hiện gọi API
                summary, tokens_sent, tokens_recv = call_cloud_gateway_api(
                    api_key=key_obj.api_key,
                    provider=key_obj.provider,
                    prompt_text=chunk,
                    system_prompt="Đọc và cô đọng lại toàn bộ logic/công thức có trong phân đoạn này, loại bỏ mọi dữ liệu nhiễu."
                )
                
                # CẬP NHẬT CHUẨN ĐỒNG BỘ: Dùng select_for_update phòng ngừa race condition
                with transaction.atomic():
                    key_record = AITokenLog.objects.select_for_update().get(id=key_obj.id)
                    key_record.requests_today += 1
                    key_record.tokens_sent_today += tokens_sent
                    key_record.tokens_received_today += tokens_recv
                    key_record.save()
                    
            map_summaries.append(summary)

    # 4. GIAI ĐOẠN 3: REDUCE (Tổng hợp tối cao)
    logger.info("聚合 [REDUCE STAGE] Đang tổng hợp các bản tóm tắt tinh khiết thành tài liệu BA...")
    combined_summaries_text = "\n\n--- PHÂN ĐOẠN TIẾP THEO ---\n\n".join(map_summaries)
    
    # Đoạn cuối luôn ưu tiên dùng Gemini Cloud có ngữ cảnh cực rộng để gom tài liệu phẳng
    final_key = get_available_key_or_fallback('GEMINI', estimated_tokens=15000)
    
    if final_key and strategy != 'OLLAMA':
        final_ba_document, ts, tr = call_cloud_gateway_api(
            api_key=final_key.api_key,
            provider='GEMINI',
            prompt_text=combined_summaries_text,
            system_prompt=config.system_prompt
        )
        with transaction.atomic():
            final_key.refresh_from_db()
            final_key.requests_today += 1
            final_key.tokens_sent_today += ts
            final_key.tokens_received_today += tr
            final_key.save()
    else:
        final_ba_document = call_local_ollama_engine(
            prompt_text=combined_summaries_text,
            system_prompt=config.system_prompt,
            model_name=config.model_name or "qwen2.5:7b"
        )
        
    return final_ba_document


def call_local_ollama_engine(prompt_text, system_prompt, model_name):
    """Giả lập hàm gọi Ollama cục bộ"""
    return f"[Ollama Result] Tổng hợp kết quả dựa trên model {model_name}"

def call_cloud_gateway_api(api_key, provider, prompt_text, system_prompt):
    """Giả lập hàm gọi API Cloud (Gemini/Groq SDK)"""
    return f"[Cloud {provider} Result] Nội dung đã xử lý sạch.", 2000, 1500