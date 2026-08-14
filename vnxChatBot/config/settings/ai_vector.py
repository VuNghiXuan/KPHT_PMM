"""
AI & Vector Store configurations.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 🧠 Vector Store & AI Engine Configs
VECTOR_DB_ENGINE = os.getenv('VECTOR_DB_ENGINE', 'chroma')  # chroma | qdrant | pgvector
VECTOR_DB_PATH = os.path.join(BASE_DIR, 'core', 'vector_db')

# LLM & API Keys
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# ⚡ Semantic Cache Config (Redis)
AI_CACHE_TIMEOUT = int(os.getenv('AI_CACHE_TIMEOUT', 86400))  # 24 hours
SEMANTIC_CACHE_THRESHOLD = float(os.getenv('SEMANTIC_CACHE_THRESHOLD', 0.92))