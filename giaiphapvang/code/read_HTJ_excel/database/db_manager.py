import re
import os
import streamlit as st
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json

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

    # ==========================================================
    # 1. Lấy dự án hiển thị siderbar
    # ==========================================================

    def get_all_projects(self):
        """Lấy danh sách tất cả các file Excel (Projects) đã upload phục vụ cho siderbar"""
        session = self.get_session()
        try:
            # Thêm sắp xếp mới nhất lên đầu cho anh dễ chọn
            return session.query(ExcelProject).order_by(ExcelProject.id.desc()).all()
        except Exception as e:
            print(f"❌ Lỗi lấy Project: {e}")
            return []
        finally:
            session.close()

    # ============================================================================================
    # 2. Đọc file Excel gốc, vét cạn xem mô tả file, đưa vào DB và xuất file JSON Backup
    # ============================================================================================

    def save_project_data(self, project_name, sheets_data):
        """
        Hàm điều hướng chính: Lưu Database xong rồi kích hoạt AI.
        """
        session = self.Session()
        project_id = None
        try:
            # BƯỚC 1: LƯU SQL (BẮT BUỘC PHẢI XONG)
            project_id = self._persist_excel_to_db(session, project_name, sheets_data)
            session.commit() # Chốt hạ việc lưu SQL
            
            print(f"✅ Đã lưu xong SQL cho Project ID: {project_id}")

        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi lưu SQL: {e}")
            raise e # Dừng luôn tại đây nếu SQL lỗi
        finally:
            session.close()

        # BƯỚC 2: GỌI AI (CHỈ CHẠY KHI BƯỚC 1 ĐÃ XONG VÀ CÓ ID)
        if project_id:
            try:
                # Lúc này mới gọi AI xử lý tri thức
                self._ingest_knowledge_async(project_id, project_name)
            except Exception as ai_err:
                # AI lỗi thì kệ nó, đừng để nó làm crash cả app
                print(f"⚠️ Cảnh báo: SQL xong nhưng AI lỗi: {ai_err}")

        return project_id

    def _persist_excel_to_db(self, session, project_name, sheets_data):
        """Chuyên trách lưu dữ liệu thô từ sheets_data vào SQLite"""
        new_project = ExcelProject(file_name=project_name)
        session.add(new_project)
        session.flush()

        for s in sheets_data:
            # Xóa sheet cũ nếu trùng tên trong cùng project (Tránh rác)
            session.query(ExcelSheet).filter_by(
                sheet_name=s.sheet_name, 
                project_id=new_project.id
            ).delete()

            new_sheet = ExcelSheet(
                sheet_name=s.sheet_name, 
                project_id=new_project.id,
                status=getattr(s, 'status', 'ACTIVE')
            )
            session.add(new_sheet)
            session.flush()

            for g in s.groups:
                new_group = DataGroup(group_name=g.group_name, sheet_id=new_sheet.id)
                session.add(new_group)
                session.flush()

                field_objects = []
                for f in g.fields:
                    col_let, _ = self._split_coord(f.coord)
                    val = int(f.value) if isinstance(f.value, float) and f.value.is_integer() else f.value
                    
                    field_objects.append(DataField(
                        coord=f.coord, row=f.row, column=f.column,
                        col_letter=col_let or self.col_to_letter(f.column),
                        label=f.label, value=str(val) if val is not None else "",
                        formula=f.formula, color_code=f.color_code,
                        field_type=f.field_type, group_id=new_group.id
                    ))
                
                if field_objects:
                    session.bulk_save_objects(field_objects)
        
        return new_project.id
    
    def _split_coord(self, coord):
        if not coord: return (None, None)
        match = re.match(r"([A-Z]+)([0-9]+)", str(coord))
        return match.groups() if match else (None, None)
    
    def _ingest_knowledge_async(self, project_id, project_name):
        """
        Xử lý tri thức AI: Làm sạch dữ liệu -> Phân loại PENDING -> Xuất JSON.
        """
        try:
            from .knowledge_manager import KnowledgeManager
            kn_manager = KnowledgeManager()
            
            # Lấy các nhãn độc nhất từ project
            unique_labels = self.extract_unique_labels_by_project(project_id)
            if not unique_labels: 
                return

            with self.get_session() as kn_session:
                # Đối soát với tri thức hiện có
                report = kn_manager.identify_new_knowledge(kn_session, unique_labels)
                
                new_definitions = []
                for item in report:
                    if item['status'] == "NEW":
                        # LÀM SẠCH NHÃN: Tránh ký tự lạ ngay từ khâu đầu vào
                        safe_term = self.clean_data(item['term'])
                        
                        new_definitions.append({
                            "term": safe_term,
                            "definition": "Đang chờ AI phân tích định nghĩa...", 
                            "category": "PENDING", # Đánh dấu để hậu xử lý
                            "metadata": [{
                                "sheet": "Auto-Detect", 
                                "project": project_name,
                                "source": "Excel-Scanner"
                            }]
                        })

                if new_definitions:
                    # Lưu vào DB với trạng thái PENDING
                    kn_manager.commit_knowledge(kn_session, new_definitions)
                    print(f"🧠 [HTJ System] Đã nạp {len(new_definitions)} nhãn mới (Trạng thái: PENDING)")
                    
                    # GỢI Ý: Anh có thể gọi hàm AI phân loại hàng loạt tại đây nếu muốn
                    # self.classify_pending_knowledge_with_ai(kn_session)

                # XUẤT JSON BACKUP (Dữ liệu lúc này đã được làm sạch)
                success, path, total = kn_manager.export_to_json(kn_session, project_id, self)
                if success:
                    print(f"📁 [HTJ System] Đã cập nhật file JSON sạch tại: {path}")

        except Exception as ai_err:
            # Lỗi AI không được làm hỏng luồng lưu Database chính của anh
            print(f"⚠️ Cảnh báo lỗi xử lý tri thức: {ai_err}")

    @classmethod  # Đổi từ staticmethod sang classmethod
    def clean_data(cls, data): # Thay data thành (cls, data)
        """Khử ký tự lạ..."""
        if isinstance(data, dict):
            # Dùng cls. để gọi đệ quy chính nó
            return {k: cls.clean_data(v) for k, v in data.items()} 
        elif isinstance(data, list):
            return [cls.clean_data(i) for i in data]
        elif isinstance(data, str):
            cleaned = data.replace('\u2028', '\n').replace('\u2029', '\n')
            return "".join(ch for ch in cleaned if ch.isprintable() or ch in "\n\r\t")
        return data
    
    # ============================================================================================
    # 3. Hiển thị dự án, sheets, giao diện table lên Gui
    # ============================================================================================

    def get_sheets_by_project(self, project_id):
        """Lấy danh sách các sheet thuộc về một project cụ thể"""
        session = self.get_session()
        try:
            return session.query(ExcelSheet).filter_by(project_id=project_id).all()
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
    
    @staticmethod
    def col_to_letter(n):
        if not n or n <= 0: return ""
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

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

                """Xem lại chỗ này à, nếu file có dòng ghi chú và quy trình thì sao"""
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
    
    def get_knowledge_by_sheet(self, sheet_id):
        """Lấy bản ghi tri thức mới nhất của một sheet"""
        session = self.Session()
        try:
            from database.models import KnowledgeBase
            # Lấy bản ghi mới nhất dựa trên created_at
            return session.query(KnowledgeBase).filter_by(sheet_id=sheet_id).order_by(KnowledgeBase.created_at.desc()).first()
        finally:
            session.close()
    
    def extract_unique_labels_by_project(self, project_id):
        """Quét nhãn sạch từ DB: Sửa lỗi Join nhập nhằng và tối ưu Regex lọc rác"""
        session = self.Session()
        try:
            # SỬA LỖI TẠI ĐÂY: Dùng select_from và chỉ định ON clause tường minh
            fields = session.query(DataField.label).\
                select_from(DataField).\
                join(DataGroup, DataField.group_id == DataGroup.id).\
                join(ExcelSheet, DataGroup.sheet_id == ExcelSheet.id).\
                filter(ExcelSheet.project_id == project_id).\
                all()
            
            blacklist = [item.lower() for item in Config.EXCEL_IGNORE_LABELS]
            unique_labels = []
            
            # Tối ưu Regex lọc số và ngày tháng (tránh nhầm nhãn "Vàng 24k")
            # Chỉ loại bỏ nếu cả cell CHỈ LÀ số thuần túy
            is_pure_number = re.compile(r'^-?\d+(\.\d+)?$')
            is_date_format = re.compile(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}')

            for f in fields:
                label = str(f[0]).strip() if f[0] else ""
                
                # 1. Bỏ trống, rác trong blacklist, chỉ có 1 ký tự hoặc mã lỗi Excel (#VALUE!, #N/A)
                if not label or label.lower() in blacklist or len(label) <= 1 or label.startswith('#'):
                    continue
                    
                # 2. Bỏ Công thức Excel
                if label.startswith('='):
                    continue
                
                # 3. Bỏ Số thuần túy (nhưng giữ lại "Vàng 999" vì 999 có chữ "Vàng")
                if is_pure_number.match(label) or is_date_format.match(label):
                    continue
                
                # 4. Loại bỏ các nhãn chỉ toàn ký tự đặc biệt hoặc icon rác
                if not re.search(r'[a-zA-ZÀ-ỹ0-9]', label):
                    continue

                unique_labels.append(label)
            
            # Kết quả trả về là danh sách duy nhất, sắp xếp A-Z
            return sorted(list(set(unique_labels)))
            
        except Exception as e:
            print(f"❌ Lỗi tại extract_unique_labels_by_project: {e}")
            return []
        finally:
            session.close()

    # ============================================================================================
    # . Các hàm liên quan đến mô tả bức thư AI
    # ============================================================================================

    def get_session(self):
        """Cung cấp session cho các service khác nếu cần"""
        return self.Session()
   