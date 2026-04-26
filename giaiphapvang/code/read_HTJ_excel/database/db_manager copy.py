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

    def get_all_projects(self):
        """Lấy danh sách tất cả các file Excel (Projects) đã upload"""
        session = self.get_session()
        try:
            # Thêm sắp xếp mới nhất lên đầu cho anh dễ chọn
            return session.query(ExcelProject).order_by(ExcelProject.id.desc()).all()
        except Exception as e:
            print(f"❌ Lỗi lấy Project: {e}")
            return []
        finally:
            session.close()

    def get_sheets_by_project(self, project_id):
        """Lấy danh sách các sheet thuộc về một project cụ thể"""
        session = self.get_session()
        try:
            return session.query(ExcelSheet).filter_by(project_id=project_id).all()
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

    def _split_coord(self, coord):
        if not coord: return (None, None)
        match = re.match(r"([A-Z]+)([0-9]+)", str(coord))
        return match.groups() if match else (None, None)

    def save_project_data(self, project_name, sheets_data):
        """
        Lưu toàn bộ file Excel thành Project và tự động kích hoạt 
        bộ não AI để nạp tri thức vào Vector DB + Xuất JSON Backup.
        """
        session = self.Session()
        try:
            # 1. TẠO PROJECT MỚI
            new_project = ExcelProject(file_name=project_name)
            session.add(new_project)
            session.flush()  # Lấy ID ngay để các bảng con sử dụng

            for s in sheets_data:
                # 2. XÓA DỮ LIỆU CŨ (Nếu trùng tên sheet để tránh rác dữ liệu)
                # Lưu ý: Chỉ xóa sheet cũ nếu anh muốn ghi đè
                old_sheet = session.query(ExcelSheet).filter_by(sheet_name=s.sheet_name).first()
                if old_sheet:
                    session.delete(old_sheet)
                    session.flush() 

                # 3. TẠO SHEET MỚI
                new_sheet = ExcelSheet(
                    sheet_name=s.sheet_name, 
                    project_id=new_project.id,
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
                        
                        # 5. TẠO FIELD (Dữ liệu thô từ Excel)
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
            
            # --- COMMIT DỮ LIỆU THÔ XUỐNG SQLITE ---
            session.commit()
            st.cache_data.clear() 
            print(f"🚀 [HTJ System] 1. Đã lưu cấu trúc Excel ID: {new_project.id}")

            # ==========================================================
            # 🧠 TỰ ĐỘNG KÍCH HOẠT BỘ NÃO AI (KNOWLEDGE INGESTION)
            # ==========================================================
            try:
                from .knowledge_manager import KnowledgeManager
                kn_manager = KnowledgeManager()
                
                # Quét lấy tất cả nhãn độc nhất từ Project vừa lưu
                unique_labels = self.extract_unique_labels_by_project(new_project.id)
                
                if unique_labels:
                    # Đối soát với Vector DB hiện tại
                    # Mở một session mới cho tri thức để tránh conflict state
                    with self.get_session() as kn_session:
                        report = kn_manager.identify_new_knowledge(kn_session, unique_labels)
                        
                        # Chỉ nạp những thứ AI báo là "NEW" (Chưa từng thấy ở các file khác)
                        # Những thứ "SIMILAR" hoặc "EXISTS" ta sẽ để Vũ duyệt thủ công sau
                        new_definitions = []
                        for item in report:
                            if item['status'] == "NEW":
                                new_definitions.append({
                                    "term": item['term'],
                                    "definition": "Chờ định nghĩa (Nạp tự động)",
                                    "category": "VÀNG", # Mặc định cho HTJ
                                    "metadata": [{"sheet": "Auto-Detect", "project": project_name}]
                                })
                        
                        if new_definitions:
                            kn_manager.commit_knowledge(kn_session, new_definitions)
                            print(f"🧠 [HTJ System] 2. Đã tự động nạp {len(new_definitions)} nhãn mới vào Vector DB.")
                        
                        # Tự động xuất file JSON Backup để anh có dữ liệu ngay lập tức
                        success, path, total = kn_manager.export_to_json(kn_session, new_project.id, self)
                        if success:
                            print(f"📁 [HTJ System] 3. Đã cập nhật file JSON Backup tại: {path} ({total} bản ghi)")

            except Exception as ai_err:
                print(f"⚠️ Cảnh báo: Dữ liệu Excel đã lưu nhưng AI không thể nạp tri thức: {ai_err}")

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

    def save_knowledge(self, sheet_id, category, content, brain_name):
        """
        Vừa lưu vào Database, vừa cập nhật file knowledge_backup.json.
        Đã bổ sung bộ lọc ký tự lạ để tránh lỗi VS Code.
        """
        session = self.Session()
        try:
            from database.models import KnowledgeBase 
            
            # Làm sạch dữ liệu trước khi xử lý (vét sạch ký tự lạ từ Excel)
            safe_content = self.clean_data(content)
            
            # 1. Lưu vào Database (SQL)
            # Chuyển safe_content thành string nếu cột content trong DB yêu cầu string
            content_for_db = json.dumps(safe_content, ensure_ascii=False) if isinstance(safe_content, (dict, list)) else safe_content
            
            new_kb = KnowledgeBase(
                sheet_id=sheet_id,
                category=category,
                content=content_for_db,
                brain_used=brain_name
            )
            session.add(new_kb)
            session.commit()

            # 2. XUẤT BACKUP JSON (Để AI đọc sau này)
            backup_file = "knowledge_backup.json"
            
            current_data = []
            if os.path.exists(backup_file):
                with open(backup_file, "r", encoding="utf-8") as f:
                    try:
                        current_data = json.load(f)
                    except: 
                        current_data = []

            # Thêm thông tin mới đã được làm sạch
            backup_entry = {
                "sheet_id": sheet_id,
                "category": category,
                "brain": brain_name,
                "data": safe_content, # "Dẻ", "Cắt ni"... giờ đã sạch bóng ký tự lạ
                "timestamp": self._get_current_time() # Nếu anh có hàm lấy giờ
            }
            current_data.append(backup_entry)

            # Ghi lại file với cấu trúc an toàn nhất
            with open(backup_file, "w", encoding="utf-8") as f:
                # indent=4 cho đẹp, ensure_ascii=False cho tiếng Việt chuẩn
                json.dump(current_data, f, ensure_ascii=False, indent=4, default=str)

            print(f"✅ [HTJ System] Đã nạp tri thức & Backup JSON (Cleaned) thành công!")
            return True
            
        except Exception as e:
            if session: session.rollback()
            print(f"❌ Lỗi khi lưu tri thức: {e}")
            return False
        finally:
            if session: session.close()
    
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
    
    def get_intelligent_knowledge_map(self, project_id, ai_service=None):
        """
        Kết hợp Cosine Similarity (nhanh) và LLM (sâu) để gom nhóm tri thức.
        """
        session = self.get_session()
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            from database.models import DataField, DataGroup, ExcelSheet, VectorKnowledge
            
            model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

            # 1. Truy vấn nhãn từ Excel
            results = (
                session.query(DataField.label, ExcelSheet.sheet_name, VectorKnowledge.definition)
                .select_from(DataField)
                .join(DataGroup, DataField.group_id == DataGroup.id)
                .join(ExcelSheet, DataGroup.sheet_id == ExcelSheet.id)
                .outerjoin(VectorKnowledge, DataField.label == VectorKnowledge.main_term)
                .filter(ExcelSheet.project_id == project_id)
                .all()
            )

            if not results: return []

            # 2. Gom nhóm thô bằng Dictionary
            raw_map = {}
            for label_raw, s_name, existing_def in results:
                label = str(label_raw).strip()
                if not label or len(label) <= 1: continue 
                if label not in raw_map:
                    raw_map[label] = {"sheets": set(), "def": existing_def or ""}
                raw_map[label]["sheets"].add(s_name)

            labels_list = list(raw_map.keys())
            embeddings = model.encode(labels_list)
            sim_matrix = cosine_similarity(embeddings)

            # 3. Gom nhóm bằng thuật toán Cosine (Ngưỡng 0.88)
            initial_clusters = []
            visited = [False] * len(labels_list)
            for i in range(len(labels_list)):
                if visited[i]: continue
                cluster = {
                    "primary_term": labels_list[i],
                    "synonyms": [],
                    "related_sheets": list(raw_map[labels_list[i]]["sheets"]),
                    "definition": raw_map[labels_list[i]]["def"]
                }
                for j in range(i + 1, len(labels_list)):
                    if not visited[j] and sim_matrix[i][j] > 0.88:
                        cluster["synonyms"].append(labels_list[j])
                        cluster["related_sheets"].extend(list(raw_map[labels_list[j]]["sheets"]))
                        visited[j] = True
                cluster["related_sheets"] = list(set(cluster["related_sheets"]))
                initial_clusters.append(cluster)
                visited[i] = True

            # 4. CHỐT CHẶN AI (Nếu có ai_service): Gom nhóm theo ngữ nghĩa nghiệp vụ
            if ai_service and len(initial_clusters) > 1:
                # Chỉ gửi danh sách nhãn chính cho AI để tiết kiệm
                terms_to_clean = [c["primary_term"] for c in initial_clusters]
                
                prompt = f"""
                Mày là chuyên gia phân tích dữ liệu ERP tiệm vàng. 
                Tao có danh sách các nhãn trích xuất từ Excel. Hãy phát hiện các nhãn thực chất là một 
                nhưng viết khác nhau (ví dụ: 'Công thợ' và 'Tiền công chế tác').
                Trả về JSON rút gọn theo định dạng: {{"từ_gốc": ["từ_đồng_nghĩa_1", "từ_đồng_nghĩa_2"]}}
                Danh sách: {terms_to_clean}
                """
                
                try:
                    ai_raw = ai_service._call_ai_api(prompt)
                    # Dùng hàm extract JSON mà mình đã viết ở bước trước
                    import re, json
                    match = re.search(r'(\{.*\})', ai_raw, re.DOTALL)
                    ai_groups = json.loads(match.group(1)) if match else {}
                    
                    # Cấu trúc lại final_clusters dựa trên "phán quyết" của AI
                    final_dict = {c["primary_term"]: c for c in initial_clusters}
                    
                    for main_term, syns in ai_groups.items():
                        if main_term in final_dict:
                            for s in syns:
                                if s in final_dict and s != main_term:
                                    # Nhập thằng đồng nghĩa vào thằng chính
                                    final_dict[main_term]["synonyms"].append(s)
                                    final_dict[main_term]["synonyms"].extend(final_dict[s]["synonyms"])
                                    final_dict[main_term]["related_sheets"].extend(final_dict[s]["related_sheets"])
                                    # Xóa thằng đồng nghĩa khỏi danh sách hiển thị chính
                                    final_dict.pop(s, None)
                    
                    return list(final_dict.values())
                except Exception as e:
                    print(f"⚠️ AI gom nhóm lỗi, dùng kết quả thuật toán: {e}")
                    return initial_clusters

            return initial_clusters

        except Exception as e:
            print(f"❌ Lỗi tại map tri thức: {e}")
            return []
        finally:
            session.close()

    def export_pending_labels_to_json(self, project_id, file_path="storage/pending_knowledge.json"):
        # Lấy các nhãn duy nhất từ project
        labels = self.extract_unique_labels_by_project(project_id)
        
        output_data = []
        for label in labels:
            output_data.append({
                "term": label,
                "definition": "", # Để trống cho Chatbot điền
                "category": "",   # Để trống cho Chatbot điền
                "synonyms": []
            })
        
        import json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        return file_path

    

    def prepare_ai_payload(self, df, task_type):
        """Lấy danh sách từ khóa thô để gửi cho AI (Tránh gửi file JSON lớn)"""
        terms = df['primary_term'].tolist()
        prompt = Config.TASK_PROMPTS.get(task_type, "Định nghĩa thuật ngữ nghiệp vụ vàng.")
        
        payload = {
            "task": task_type,
            "prompt": prompt,
            "terms": terms  # Chỉ gửi danh sách từ, AI không cần đọc cấu hình JSON
        }
        return payload

    def merge_ai_results(self, original_df, ai_results):
        """Hàm đọc kết quả AI trả về và map ngược lại vào DataFrame gốc theo từng Key"""
        # ai_results dự kiến là một dict: {"Từ khóa": "Định nghĩa"}
        for idx, row in original_df.iterrows():
            term = row['primary_term']
            if term in ai_results:
                original_df.at[idx, 'definition'] = ai_results[term]
                # Tự động tích luôn nếu AI đã định nghĩa xong
                original_df.at[idx, 'is_approved'] = True 
        return original_df
    
    def get_session(self):
        """Cung cấp session cho các service khác nếu cần"""
        return self.Session()
   