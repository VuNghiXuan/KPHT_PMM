"""
Module: config.settings.celery_channels
Description: Cấu hình chuẩn hóa cho Celery Task Queues & Django Channels (Redis WebSocket Layer).
Tuân thủ tuyệt đối quy tắc phân tách luồng P0 (Realtime) và P1 (Background Processing).
"""

import os
from pathlib import Path
from config.settings.base import SECRET_KEY

# --- CELERY CONFIGURATION ---
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# --- CHANNELS & WEBSOCKET CONFIGURATION ---
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # Truyền trực tiếp timeout qua query parameters của Redis URL
            "hosts": [f"redis://{REDIS_HOST}:{REDIS_PORT}/0?socket_timeout=60&socket_connect_timeout=60"],
            "capacity": 1500,  # Sức chứa hàng đợi tin nhắn WebSocket
            "expiry": 60,      # Thời gian hết hạn message (giây)
        },
    },
}

# --- CELERY TASK ROUTING (Luồng số 1 & Luồng số 2) ---
CELERY_TASK_ROUTES = {
    'apps.ai_assistant.tasks.process_document_task': {
        'queue': 'documents_p1_processing',
    },
    'apps.ai_assistant.tasks.sync_vector_db_task': {
        'queue': 'documents_p1_processing',
    },
    'apps.ai_assistant.tasks.conflict_analysis_task': {
        'queue': 'conflicts',
    },
}