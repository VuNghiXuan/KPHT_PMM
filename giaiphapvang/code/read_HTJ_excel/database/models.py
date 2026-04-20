from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class ExcelSheet(Base):
    __tablename__ = 'excel_sheets'
    id = Column(Integer, primary_key=True)
    sheet_name = Column(String(255))
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
    
    group = relationship("DataGroup", back_populates="fields")