from sqlalchemy import Column, Integer, String, Text, LargeBinary
from database.models import Base


class VectorKnowledge(Base):
    __tablename__ = "vector_knowledge"
    id = Column(Integer, primary_key=True)
    category = Column(String(50))  # GLOSSARY, FORMULA, CHAT_SCRIPT
    question = Column(Text)        # Thuật ngữ hoặc câu hỏi chatbot
    answer = Column(Text)          # Định nghĩa hoặc kịch bản trả lời
    embedding = Column(LargeBinary) # Lưu vector đã encode (dạng bytes)