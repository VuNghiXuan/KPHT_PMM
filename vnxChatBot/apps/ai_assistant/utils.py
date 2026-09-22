# apps/ai_assistant/utils.py
import re
import logging
import redis

logger = logging.getLogger(__name__)

def clean_json_markdown(raw_response: str) -> str:
    """
    🧹 Loại bỏ các thẻ markdown code block (```json ... ``` hoặc ``` ... ```) 
    từ phản hồi của LLM để trả về chuỗi JSON thuần túy.
    """
    if not isinstance(raw_response, str):
        return raw_response
    
    # Biểu thức chính quy bắt khối mã markdown linh hoạt
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, raw_response)
    
    if match:
        return match.group(1).strip()
    return raw_response.strip()

def check_redis_status(host='127.0.0.1', port=6379, timeout=2):
    """Kiểm tra xem Redis server ⚡ có đang hoạt động hay không."""
    try:
        client = redis.Redis(host=host, port=port, socket_timeout=timeout)
        return client.ping()
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return False