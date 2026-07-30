# apps\ai_assistant\utils.py
import redis

def check_redis_status(host='127.0.0.1', port=6379, timeout=2):
    """Kiểm tra xem Redis server có đang hoạt động hay không."""
    try:
        client = redis.Redis(host=host, port=port, socket_timeout=timeout)
        return client.ping()
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return False