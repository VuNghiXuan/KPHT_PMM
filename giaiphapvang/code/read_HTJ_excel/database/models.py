from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import PickleType 

Base = declarative_base()

class ExcelProject(Base):
    __tablename__ = 'excel_projects'
    id = Column(Integer, primary_key=True)
    file_name = Column(String(255)) # Tên file Excel Vũ upload lên
    created_at = Column(DateTime, server_default=func.now())
    sheets = relationship("ExcelSheet", back_populates="project")

class ExcelSheet(Base):
    __tablename__ = 'excel_sheets'

    id = Column(Integer, primary_key=True)
    sheet_name = Column(String(255))
    project_id = Column(Integer, ForeignKey('excel_projects.id')) # Thêm dòng này
    project = relationship("ExcelProject", back_populates="sheets")

    status = Column(String(50))
    groups = relationship("DataGroup", back_populates="sheet")

class DataGroup(Base):
    __tablename__ = 'data_groups'
    id = Column(Integer, primary_key=True)
    group_name = Column(String(255))
    sheet_id = Column(Integer, ForeignKey('excel_sheets.id'))
    sheet = relationship("ExcelSheet", back_populates="groups")
    fields = relationship("DataField", back_populates="group")

class DataField(Base):
    __tablename__ = 'data_fields'
    id = Column(Integer, primary_key=True)
    coord = Column(String(20))
    row = Column(Integer)
    column = Column(Integer)
    col_letter = Column(String(10))  # <--- THÊM CỘT NÀY ĐỂ FIX LỖI
    label = Column(String(255), nullable=True)
    value = Column(Text, nullable=True)
    formula = Column(Text, nullable=True)
    color_code = Column(String(50))
    field_type = Column(String(50))
    group_id = Column(Integer, ForeignKey('data_groups.id'))
    business_key = Column(String(100), index=True)
    
    group = relationship("DataGroup", back_populates="fields")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True)
    sheet_id = Column(Integer, ForeignKey("excel_sheets.id"))
    category = Column(String(100)) # Ví dụ: "Quy trình vận hành"
    content = Column(Text) # Nội dung AI soạn (Markdown)
    brain_used = Column(String(50)) # AI nào soạn (Gemini/Groq...)
    created_at = Column(DateTime, server_default=func.now())

class GlobalGlossary(Base):
    __tablename__ = "global_glossary"
    id = Column(Integer, primary_key=True)
    term = Column(String(255), unique=True)
    definition = Column(Text)
    
    # QUAN TRỌNG: Thêm dòng này để khớp với 'back_populates' ở bảng dưới
    questions = relationship("KnowledgeQuestion", back_populates="glossary", cascade="all, delete-orphan")

class KnowledgeQuestion(Base):
    __tablename__ = "knowledge_questions"
    id = Column(Integer, primary_key=True)
    glossary_id = Column(Integer, ForeignKey("global_glossary.id"))
    question_text = Column(Text)
    
    # Quan hệ ngược lại: tên 'glossary' phải khớp với 'back_populates' ở bảng trên
    glossary = relationship("GlobalGlossary", back_populates="questions")

# Bảng lưu Quy trình/Hướng dẫn (Biên soạn theo từng Sheet)
class SheetProcess(Base):
    __tablename__ = "sheet_processes"
    id = Column(Integer, primary_key=True)
    sheet_id = Column(Integer, ForeignKey("excel_sheets.id"))
    step_description = Column(Text) # Quy trình Step-by-step
    ai_model = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

class VectorKnowledge(Base):
    __tablename__ = "vector_knowledge"
    
    id = Column(Integer, primary_key=True)
    category = Column(String(50), default="VÀNG") 
    
    # Dùng main_term cho đúng với code Service/DBManager anh đang dùng
    main_term = Column(String(255), index=True, unique=True) 
    definition = Column(Text)                           
    
    synonyms = Column(JSON, nullable=True)              
    sample_questions = Column(JSON, nullable=True) 
    source_mapping = Column(JSON, nullable=True) 
    
    logic_rules = Column(Text, nullable=True)
    business_rules = Column(Text, nullable=True)
    
    # vector = Column(JSON, nullable=True) 
    embedding = Column(PickleType, nullable=True) # Lưu dạng số toạ độ vector

    # Thêm trường này để lưu trạng thái duyệt của anh Vũ
    is_approved = Column(Integer, default=0) # 0: Nháp, 1: Đã duyệt
    raw_ai_suggestion = Column(JSON, nullable=True) # Lưu bản gốc của AI
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<VectorKnowledge(main_term='{self.main_term}')>"

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True)
    user_query = Column(Text)
    ai_response = Column(Text)
    referenced_knowledge_id = Column(Integer, ForeignKey("vector_knowledge.id"), nullable=True)
    feedback = Column(Integer, default=0) 
    created_at = Column(DateTime, server_default=func.now())