# import json
# from sqlalchemy import Column, Integer, String, Text, LargeBinary, DateTime, ForeignKey, JSON
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from database.models import Base # Đảm bảo Base này trỏ đúng về file khai báo Base gốc

# class VectorKnowledge(Base):
#     __tablename__ = "vector_knowledge"
    
#     id = Column(Integer, primary_key=True)
#     category = Column(String(50), default="VÀNG") 
    
#     # --- ĐỒNG BỘ TÊN CỘT VỚI LOGIC CODE ---
#     term = Column(String(255), index=True, unique=True) # Đổi main_term thành term
#     definition = Column(Text)                           # Định nghĩa/Câu trả lời
    
#     # Hỗ trợ AI & Nhận diện
#     # Dùng JSON để lưu list cho khỏe, đỡ phải split dấu phẩy
#     synonyms = Column(JSON, nullable=True)              
#     sample_questions = Column(JSON, nullable=True) 
    
#     # Nguồn gốc dữ liệu
#     source_mapping = Column(JSON, nullable=True) 
    
#     # Logic & Quy tắc
#     logic_rules = Column(Text, nullable=True)
#     business_rules = Column(Text, nullable=True)
    
#     # Dữ liệu kỹ thuật
#     # Đổi embedding thành vector (JSON) để khớp với code tính toán AI hiện tại
#     vector = Column(JSON, nullable=True) 
    
#     created_at = Column(DateTime, server_default=func.now())
#     updated_at = Column(DateTime, onupdate=func.now())

#     def __repr__(self):
#         return f"<VectorKnowledge(term='{self.term}')>"

# # =================================================================
# # 💬 NHẬT KÝ HỎI ĐÁP (Dữ liệu để huấn luyện AI của Vũ)
# # =================================================================
# class ChatHistory(Base):
#     __tablename__ = "chat_history"
    
#     id = Column(Integer, primary_key=True)
#     user_query = Column(Text)
#     ai_response = Column(Text)
    
#     # Metadata để anh biết AI trả lời dựa trên nguồn nào
#     referenced_knowledge_id = Column(Integer, ForeignKey("vector_knowledge.id"), nullable=True)
    
#     # Phản hồi từ Vũ hoặc người dùng
#     feedback = Column(Integer, default=0) # 1: Hài lòng, -1: Không hài lòng, 0: Chưa đánh giá
#     admin_note = Column(Text, nullable=True) # Anh ghi chú lại để sửa tri thức nếu AI nói sai
    
#     created_at = Column(DateTime, server_default=func.now())
