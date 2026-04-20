import re
import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, ExcelSheet, DataGroup, DataField

class DBManager:
    def __init__(self, db_url="sqlite:///storage/htj_data.db"):
        # Đảm bảo thư mục storage tồn tại
        os.makedirs("storage", exist_ok=True)
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    @staticmethod
    def col_to_letter(n):
        if not n or n <= 0: return ""
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

    def _split_coord(self, coord):
        if not coord: return (None, None)
        match = re.match(r"([A-Z]+)([0-9]+)", str(coord))
        return match.groups() if match else (None, None)

    def save_project_data(self, sheets_data):
        """Lưu dữ liệu và dọn dẹp cache cũ"""
        session = self.Session()
        try:
            for s in sheets_data:
                # 1. Tạo Sheet mới
                new_sheet = ExcelSheet(
                    sheet_name=s.sheet_name, 
                    status=getattr(s, 'status', 'ACTIVE')
                )
                session.add(new_sheet)
                session.flush() 

                for g in s.groups:
                    # 2. Tạo Group
                    new_group = DataGroup(group_name=g.group_name, sheet_id=new_sheet.id)
                    session.add(new_group)
                    session.flush()

                    field_objects = []
                    for f in g.fields:
                        col_let, _ = self._split_coord(f.coord)
                        
                        # Xử lý giá trị: Nếu là số thì định dạng lại cho đẹp (bỏ .0)
                        val = f.value
                        if isinstance(val, float) and val.is_integer():
                            val = int(val)
                        
                        new_field = DataField(
                            coord=f.coord, 
                            row=f.row, 
                            column=f.column,
                            col_letter=col_let or self.col_to_letter(f.column),
                            label=f.label,
                            value=str(val) if val is not None else "",
                            formula=f.formula, 
                            color_code=f.color_code,
                            field_type=f.field_type, 
                            group_id=new_group.id
                        )
                        field_objects.append(new_field)
                    
                    # Lưu hàng loạt để tăng tốc
                    if field_objects:
                        session.bulk_save_objects(field_objects)
            
            session.commit()
            st.cache_data.clear()
            print(f"🚀 [HTJ System] Đã đồng bộ thành công.")
        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi DB: {e}")
            raise e
        finally:
            session.close()

    def get_all_sheets(self):
        session = self.Session()
        try:
            return session.query(ExcelSheet).all()
        finally:
            session.close()

    def get_data_by_sheet_as_table(self, sheet_id):
        """Dựng ma trận hiển thị trên Streamlit cực chuẩn"""
        session = self.Session()
        try:
            sheet = session.query(ExcelSheet).filter_by(id=sheet_id).first()
            if not sheet: return [], []

            # Lấy tất cả fields của sheet này
            fields = session.query(DataField).join(DataGroup).filter(DataGroup.sheet_id == sheet_id).all()
            
            if not fields: return [], []

            max_row = 0
            columns_found = set()
            table_map = {}

            for f in fields:
                if f.row > max_row: max_row = f.row
                columns_found.add(f.column)
                
                if f.row not in table_map: 
                    table_map[f.row] = {}
                
                table_map[f.row][f.column] = {
                    "value": f.value if f.value else "",
                    "coord": f.coord,
                    "color": f.color_code
                }

            sorted_cols = sorted(list(columns_found))
            final_rows = []
            
            # Duyệt từ dòng 1 đến dòng lớn nhất để không bỏ sót ô trống
            for r in range(1, max_row + 1):
                row_data = {"row_index": r, "cells": []}
                for c in sorted_cols:
                    # Lấy cell từ map, nếu không có thì tạo cell trống
                    cell = table_map.get(r, {}).get(c, {"value": "", "coord": "", "color": "N/A"})
                    row_data["cells"].append(cell)
                final_rows.append(row_data)

            header_letters = [self.col_to_letter(c) for c in sorted_cols]
            return final_rows, header_letters
        finally:
            session.close()

    def get_sheet_data_as_json(self, sheet_id):
        session = self.Session()
        try:
            fields = session.query(DataField).join(DataGroup).filter(DataGroup.sheet_id == sheet_id).all()
            return [{
                "coord": f.coord,
                "value": f.value,
                "group": f.group.group_name
            } for f in fields]
        finally:
            session.close()

    def get_sheet_data_as_cleaned_text(self, sheet_id):
        """Nén dữ liệu gửi AI"""
        session = self.Session()
        try:
            sheet = session.query(ExcelSheet).filter_by(id=sheet_id).first()
            if not sheet: return "Không có dữ liệu."

            summary = {}
            current_module = "Chung"
            
            fields = session.query(DataField).join(DataGroup).filter(DataGroup.sheet_id == sheet_id).order_by(DataField.row).all()

            for f in fields:
                val = str(f.value).strip() if f.value else ""
                if not val or val.lower() in ["none", "null", "stt", "module", "nhóm chức năng"]:
                    continue

                # Cột B là Module, Cột C là Chức năng
                if f.col_letter == "B":
                    current_module = val
                    if current_module not in summary: summary[current_module] = []
                elif f.col_letter == "C":
                    if current_module not in summary: summary[current_module] = []
                    summary[current_module].append(val)

            if not summary: return "Dữ liệu trống."

            text_output = f"HỆ THỐNG HTJ - SHEET: {sheet.sheet_name}\n"
            for mod, funcs in summary.items():
                unique_funcs = list(dict.fromkeys(funcs))
                text_output += f"• {mod}: {' > '.join(unique_funcs)}\n"

            return text_output
        finally:
            session.close()