import re
import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from database.models import Base, ExcelProject, ExcelSheet, DataGroup, DataField
from config import Config

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

    def save_project_data(self, project_name, sheets_data):
        """Lưu toàn bộ file Excel thành một Project và các Sheet liên quan"""
        session = self.Session()
        try:
            # 1. TẠO PROJECT MỚI (Đại diện cho 1 file Excel Vũ upload)
            # Nhập model ExcelProject nếu chưa có ở đầu file
            
            
            new_project = ExcelProject(file_name=project_name)
            session.add(new_project)
            session.flush()  # Để lấy được new_project.id

            for s in sheets_data:
                # 2. XÓA DỮ LIỆU CŨ (Nếu Vũ muốn ghi đè sheet trùng tên trong cùng hệ thống)
                # Tùy Vũ: Có thể bỏ qua bước xóa nếu muốn lưu mọi lần upload thành project riêng
                old_sheet = session.query(ExcelSheet).filter_by(sheet_name=s.sheet_name).first()
                if old_sheet:
                    session.delete(old_sheet)
                    session.flush() 

                # 3. TẠO SHEET MỚI và gắn vào Project ID
                new_sheet = ExcelSheet(
                    sheet_name=s.sheet_name, 
                    project_id=new_project.id,  # <--- GẮN KẾT QUAN TRỌNG Ở ĐÂY
                    status=getattr(s, 'status', 'ACTIVE')
                )
                session.add(new_sheet)
                session.flush() 

                for g in s.groups:
                    # 4. TẠO GROUP
                    new_group = DataGroup(group_name=g.group_name, sheet_id=new_sheet.id)
                    session.add(new_group)
                    session.flush()

                    field_objects = []
                    for f in g.fields:
                        col_let, _ = self._split_coord(f.coord)
                        
                        val = f.value
                        if isinstance(val, float) and val.is_integer():
                            val = int(val)
                        
                        # 5. TẠO FIELD
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
                    
                    if field_objects:
                        session.bulk_save_objects(field_objects)
            
            session.commit()
            st.cache_data.clear() 
            print(f"🚀 [HTJ System] Đã lưu Project '{project_name}' với ID: {new_project.id}")
            return new_project.id
        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi DB khi lưu Project: {e}")
            raise e
        finally:
            session.close()

    def get_all_sheets(self):
        session = self.Session()
        try:
            # Sử dụng joinedload để nạp luôn dữ liệu project vào object sheet
            return session.query(ExcelSheet).options(joinedload(ExcelSheet.project)).all()
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
        """Nén dữ liệu siêu gọn: Cắt số lẻ, lấy 1 mẫu duy nhất để tránh Timeout"""
        session = self.Session()
        try:
            sheet = session.query(ExcelSheet).filter_by(id=sheet_id).first()
            if not sheet: return "Không có dữ liệu."

            summary = {}
            module_count = {} 
            current_module = "Chung"
            
            fields = session.query(DataField).join(DataGroup).filter(
                DataGroup.sheet_id == sheet_id
            ).order_by(DataField.row, DataField.column).all()

            for f in fields:
                val = str(f.value).strip() if f.value else ""
                # Lọc bỏ dữ liệu rác/trống
                if not val or val.lower() in ["none", "null", "stt", "-", "true", "false"]: continue
                if len(val) > 200: val = val[:197] + "..." # Chặn các đoạn text quá dài

                # Nhận diện Module
                if f.col_letter == "B" and len(val) > 2:
                    current_module = val
                    if current_module not in summary:
                        summary[current_module] = []
                        module_count[current_module] = 0
                    module_count[current_module] += 1
                else:
                    if current_module not in summary: 
                        summary[current_module] = []
                        module_count[current_module] = 1
                    
                    # --- CHIẾN THUẬT 1: CHỈ LẤY 1 BẢN GHI MẪU ---
                    if module_count.get(current_module, 0) > 1 and current_module not in ["Chung", "THÔNG TIN CHUNG", "FORM PHIẾU BÁN VÀNG NGUYÊN LIỆU"]:
                        continue

                    # --- CHIẾN THUẬT 2: LÀM TRÒN SỐ ĐỂ GIẢM TOKEN ---
                    try:
                        if "." in val:
                            num_val = float(val)
                            val = str(round(num_val, 2)) # Chỉ giữ 2 số lẻ
                    except:
                        pass

                    prefix = ""
                    if f.field_type == "ACTION": prefix = "[NÚT BẤM]"
                    elif f.field_type == "AUTO_CALC": prefix = "[TỰ TÍNH]"
                    
                    label = f.label if f.label and f.label != "Unknown" else ""
                    info = f"{prefix} {label}: {val}".strip()
                    summary[current_module].append(info)

            if not summary: return "Dữ liệu trống."

            # --- CHIẾN THUẬT 3: XÂY DỰNG OUTPUT SIÊU GỌN ---
            text_output = f"HỆ THỐNG HTJ - FORM: {sheet.sheet_name}\n"
            for mod, funcs in summary.items():
                # Xóa trùng lặp trong chính module đó
                unique_funcs = []
                seen = set()
                for item in funcs:
                    if item not in seen:
                        unique_funcs.append(item)
                        seen.add(item)

                total = module_count.get(mod, 0)
                text_output += f"\n📂 {mod}" + (f" (Mẫu 1/{total})" if total > 1 else "")
                text_output += "\n  + " + "\n  + ".join(unique_funcs) + "\n"

            return text_output
        finally:
            session.close()
    
    def save_knowledge(self, sheet_id, category, content, brain_name):
        """Lưu kết quả AI vào làm file kiến thức (Knowledge Base)"""
        session = self.Session()
        try:
            # Nhập model KnowledgeBase nếu chưa có ở đầu file
            from database.models import KnowledgeBase 
            
            new_kb = KnowledgeBase(
                sheet_id=sheet_id,
                category=category,
                content=content,
                brain_used=brain_name
            )
            session.add(new_kb)
            session.commit()
            print(f"✅ [HTJ System] Đã lưu tri thức cho sheet {sheet_id}")
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi khi lưu tri thức: {e}")
            return False
        finally:
            session.close()
    
    def get_knowledge_by_sheet(self, sheet_id):
        """Lấy bản ghi tri thức mới nhất của một sheet"""
        session = self.Session()
        try:
            from database.models import KnowledgeBase
            # Lấy bản ghi mới nhất dựa trên created_at
            return session.query(KnowledgeBase).filter_by(sheet_id=sheet_id).order_by(KnowledgeBase.created_at.desc()).first()
        finally:
            session.close()
    
    # Hàm hỗ trợ lấy danh sách từ mới để định nghĩa lưu cho vectorDB :
    def extract_unique_labels(self, sheet_id):
        session = self.Session()
        try:
            # Lấy toàn bộ label từ DB
            fields = session.query(DataField.label).join(DataGroup).filter(
                DataGroup.sheet_id == sheet_id
            ).all()
            
            unique_labels = []
            # Lấy danh sách cấm từ Config và chuyển về chữ thường để so sánh cho chuẩn
            blacklist = [item.lower() for item in Config.EXCEL_IGNORE_LABELS]

            for f in fields:
                label = str(f[0]).strip()
                # CHỈ LẤY: có chữ, không nằm trong blacklist, không phải chỉ là số thuần túy
                if (label and 
                    label.lower() not in blacklist and 
                    not label.isdigit() and 
                    len(label) > 1):
                    unique_labels.append(label)

            return sorted(list(set(unique_labels)))
        finally:
            session.close()

    def extract_unique_labels_by_sheet(self, sheet_id): # Đổi tên hàm cho đúng bản chất
        session = self.Session()
        try:
            # Query lấy nhãn từ Field -> Group -> Sheet (theo sheet_id)
            fields = session.query(DataField.label).join(DataGroup).filter(
                DataGroup.sheet_id == sheet_id
            ).all()
            
            blacklist = [item.lower() for item in Config.EXCEL_IGNORE_LABELS]
            unique_labels = []
            for f in fields:
                if f[0]:
                    label = str(f[0]).strip()
                    # Lọc rác và số
                    if label and label.lower() not in blacklist and not label.isdigit():
                        unique_labels.append(label)
            
            return sorted(list(set(unique_labels)))
        finally:
            session.close()
            
    def extract_unique_labels_by_project(self, project_id):
        """Quét và lọc sạch rác (số, ngày, công thức) để lấy thuật ngữ chuẩn"""
        session = self.Session()
        try:
            # Truy vấn nhãn từ Field -> Group -> Sheet -> Project
            fields = session.query(DataField.label).join(DataGroup).join(ExcelSheet).filter(
                ExcelSheet.project_id == project_id
            ).all()
            
            # Lấy danh sách cấm từ Config
            blacklist = [item.lower() for item in Config.EXCEL_IGNORE_LABELS]
            unique_labels = []
            
            for f in fields:
                label = str(f[0]).strip() if f[0] else ""
                
                # 1. Bỏ trống, rác trong blacklist hoặc chỉ có 1 ký tự
                if not label or label.lower() in blacklist or len(label) <= 1:
                    continue
                    
                # 2. Bỏ Công thức Excel (Bắt đầu bằng dấu =)
                if label.startswith('='):
                    continue
                    
                # 3. Bỏ Số thuần túy (1.0, 28.0, 1460000...)
                if re.match(r'^-?\d+(\.\d+)?$', label):
                    continue
                    
                # 4. Bỏ định dạng Ngày tháng
                if re.match(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', label):
                    continue

                unique_labels.append(label)
                
            # Trả về danh sách không trùng lặp và đã sắp xếp
            return sorted(list(set(unique_labels)))
        finally:
            session.close()

    def get_session(self):
        """Cung cấp session cho các service khác nếu cần"""
        return self.Session()
   