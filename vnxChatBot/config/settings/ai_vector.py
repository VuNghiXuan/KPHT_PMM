"""
AI & Vector Store configurations.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 🧠 Vector Store & AI Engine Configs
VECTOR_DB_ENGINE = os.getenv('VECTOR_DB_ENGINE', 'chroma')  # chroma | qdrant | pgvector
VECTOR_DB_PATH = os.path.join(BASE_DIR, 'core', 'vector_db')

# 🔑 API Keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
XAI_API_KEY = os.getenv('XAI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 🤖 Provider & Model Configurations
DEFAULT_PROVIDER = os.getenv('DEFAULT_PROVIDER', 'ollama').lower()
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# Mô hình Embedding
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'ollama/bge-m3')

# Tên mô hình theo từng Provider
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'qwen/qwen3.8-27b')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')


# 🎯 Tự động định dạng Model Name chuẩn tiền tố LiteLLM
def get_default_llm_model() -> str:
    """Trả về mô hình LLM mặc định kèm prefix tương ứng cho LiteLLM."""
    provider = DEFAULT_PROVIDER
    if provider == 'ollama':
        model = OLLAMA_MODEL
        return model if model.startswith('ollama/') else f"ollama/{model}"
    elif provider == 'gemini':
        model = GEMINI_MODEL
        return model if model.startswith('gemini/') else f"gemini/{model}"
    elif provider == 'groq':
        model = GROQ_MODEL
        return model if model.startswith('groq/') else f"groq/{model}"
    return f"ollama/{OLLAMA_MODEL}"


DEFAULT_LLM_MODEL = get_default_llm_model()

# ⚡ Semantic Cache Config (Redis)
AI_CACHE_TIMEOUT = int(os.getenv('AI_CACHE_TIMEOUT', 86400))  # 24 hours
SEMANTIC_CACHE_THRESHOLD = float(os.getenv('SEMANTIC_CACHE_THRESHOLD', 0.92))