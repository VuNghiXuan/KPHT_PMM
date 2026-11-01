# apps/ai_assistant/vector_store/__init__.py
from .chromadb_client import ChromaDBClient as VectorDBManager

__all__ = ['VectorDBManager']