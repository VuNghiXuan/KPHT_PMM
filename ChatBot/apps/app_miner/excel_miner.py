import re
import openpyxl
import datetime
import traceback
import logging
from openpyxl.cell.cell import MergedCell
from django.db import transaction
import time

# Import các Model đã thống nhất
from apps.app_coach.models import DataType
from .models import ExcelSheet, DataField, ExcelTableRegion
from apps.app_knowledge.models import KnowledgeDraft
from .graph_service import Neo4jService

logger = logging.getLogger(__name__)

class ExcelMinerService:
    def __init__(self):
        self.keywords_dict = {}
        self.important_codes = []
        self.default_dtype = None
        self.formula_dtype = None

    @classmethod
    def run_workflow(cls, project):
        """
        Hàm tĩnh để gọi từ Model hoặc Admin (Point of Entry).
        """
        miner = cls()
        project.status = 'PROCESSING'
        project.save()
        
        success, message = miner.process_project(project)
        
        if success:
            project.status = 'COMPLETED'
        else:
            project.status = 'FAILED'
        project.save()
        return success, message
    
    def _prepare_resources(self):
        """Tải cấu hình từ DB."""
        data_types = DataType.objects.all()
        self.keywords_dict = {
            dt.name.lower(): {
                'code': dt.code, 
                'is_important': getattr(dt, 'is_important', False)
            } for dt in data_types
        }
        self.important_codes = [v['code'] for k, v in self.keywords_dict.items() if v['is_important']]
        
        self.default_dtype, _ = DataType.objects.get_or_create(code='MOCK', defaults={'name': 'Dữ liệu thô'})
        self.formula_dtype, _ = DataType.objects.get_or_create(code='FORMULA', defaults={'name': 'Công thức'})

    def process_project(self, project):
        # 'giỏ' chứa dữ liệu để đẩy lên Neo4j một lần cho nhanh
        all_fields_data = [] 
        self._prepare_resources()
        
        try:
            # data_only=False để lấy được công thức (formula) phục vụ AI Logic
            wb = openpyxl.load_workbook(project.file_path.path, data_only=False)
            total_sheets = len(wb.sheetnames)
            seen_drafts = set() 
            all_drafts = []

            for index, sheet_name in enumerate(wb.sheetnames):
                ws = wb[sheet_name]
                
                # 1. Tạo Sheet và xác định Vùng nghiệp vụ (Region)
                sheet_obj, _ = ExcelSheet.objects.update_or_create(
                    project=project, 
                    name=sheet_name,
                    defaults={'category': 'GOLD_TRADING'} 
                )

                # Xóa dữ liệu cũ của sheet này trong SQL để nạp mới (tránh trùng lặp)
                DataField.objects.filter(sheet=sheet_obj).delete()
                
                # TỰ ĐỘNG NHẬN DIỆN VÙNG (Ví dụ: Dựa vào các ô có màu làm Header)
                current_region = self._detect_and_create_region(ws, sheet_obj)

                fields_to_create = []
                merged_ranges = ws.merged_cells.ranges

                # Tối ưu vùng đọc: iter_rows giúp kiểm soát vùng nhớ tốt hơn
                for row in ws.iter_rows(max_row=ws.max_row, max_col=ws.max_column):
                    # Kiểm tra dòng trống để break sớm (tăng tốc độ xử lý file lớn)
                    if not any(cell.value for cell in row): 
                        continue 

                    for cell in row:
                        # Bỏ qua các ô phụ trong một vùng đã gộp (Merged Cells)
                        if any(cell.coordinate in r and cell.coordinate != r.start_cell.coordinate for r in merged_ranges):
                            continue

                        # Chỉ xử lý nếu ô có giá trị hoặc có ghi chú (Comment)
                        if cell.value is not None or (hasattr(cell, 'comment') and cell.comment):
                            # Tạo đối tượng DataField (trong bộ nhớ)
                            field_obj = self._prepare_cell_logic(ws, sheet_obj, cell, current_region)
                            fields_to_create.append(field_obj)
                            
                            # --- GOM DỮ LIỆU CHO NEO4J ---
                            all_fields_data.append({
                                'sheet_name': sheet_name,
                                'row': cell.row,
                                'col': cell.column_letter,
                                'coordinate': cell.coordinate,
                                'val': str(cell.value) if cell.value is not None else "",
                                'formula': str(cell.formula) if hasattr(cell, 'formula') and cell.formula else ""
                            })

                            # Logic tạo bản thảo cho AI (KnowledgeDraft) dựa trên công thức hoặc comment
                            if (hasattr(field_obj, 'formula') and field_obj.formula) or (hasattr(cell, 'comment') and cell.comment):
                                draft_key = f"{sheet_name}_{field_obj.formula}_{cell.coordinate}"
                                if draft_key not in seen_drafts:
                                    draft = self._create_knowledge_draft_internal(project, field_obj, cell)
                                    if draft: 
                                        all_drafts.append(draft)
                                        seen_drafts.add(draft_key)

                    # Lưu vào SQL theo lô (Batch) để tránh lỗi "database is locked" trên SQLite
                    if len(fields_to_create) >= 300: 
                        try:
                            with transaction.atomic():
                                DataField.objects.bulk_create(fields_to_create)
                            fields_to_create = []
                            # Nghỉ một chút để SQLite giải phóng khóa (lock)
                            time.sleep(0.1) 
                        except Exception as db_e:
                            print(f"--- ĐỢI DATABASE SQLITE: {db_e} ---")
                            time.sleep(1)

                # Lưu số lượng còn lại của sheet sau khi kết thúc vòng lặp
                if fields_to_create:
                    DataField.objects.bulk_create(fields_to_create)
            
            # 2. Lưu bản thảo kiến thức cho AI
            if all_drafts:
                KnowledgeDraft.objects.bulk_create(all_drafts, ignore_conflicts=True)
            
            # 3. ĐẨY LÊN NEO4J (Sử dụng hàm UNWIND tối ưu)
            if all_fields_data:
                print(f"--- BẮT ĐẦU ĐẨY {len(all_fields_data)} Ô LÊN NEO4J ---")
                project.refresh_from_db() 
                self._push_to_neo4j_fast(project.id, all_fields_data)

            return True, f"Xong {total_sheets} sheets. Tìm thấy {len(all_drafts)} logic nghiệp vụ."
            
        except Exception as e:
            logger.error(f"Lỗi Miner: {str(e)}")
            print(f"--- LỖI XẢY RA: {str(e)} ---")
            return False, traceback.format_exc()

    def _push_to_neo4j_fast(self, project_id, batch_data):
        # Câu lệnh Cypher tối ưu dùng UNWIND
        query = """
        UNWIND $batch AS item
        MERGE (p:Project {id: $p_id})
        MERGE (s:Sheet {name: item.sheet_name, project_id: $p_id})
        MERGE (p)-[:HAS_SHEET]->(s)
        CREATE (f:DataField {
            row: item.row, 
            col: item.col, 
            coordinate: item.coordinate,
            value: item.val,
            formula: item.formula
        })
        CREATE (s)-[:HAS_FIELD]->(f)
        """
        
        try:
            # Anh phải khởi tạo service ở đây để có cái 'driver'
            from .graph_service import Neo4jService 
            neo4j_svc = Neo4jService() 
            
            # Dùng driver từ service vừa khởi tạo
            with neo4j_svc.driver.session() as session:
                # Vì 34k ô là khá lớn, ta nên chia nhỏ ra đẩy cho chắc ăn
                batch_size = 2000 
                for i in range(0, len(batch_data), batch_size):
                    chunk = batch_data[i:i + batch_size]
                    session.run(query, batch=chunk, p_id=project_id)
                    print(f"--- Đã đẩy thành công {i + len(chunk)} / {len(batch_data)} ô lên Neo4j ---")
                    
        except Exception as e:
            print(f"--- LỖI ĐẨY NEO4J: {str(e)} ---")
            raise e # Re-raise để Miner ghi nhận lỗi vào log
                
    # # Sau khi xong SQL, đẩy lên Neo4j
    # def _push_data_to_neo4j(self, project):
    #     try:
    #         neo4j_svc = Neo4jService()
    #         neo4j_svc.sync_full_logic(project)
            
    #         # Tạo thêm quan hệ công thức cho từng sheet
    #         for sheet in project.sheets.all():
    #             neo4j_svc.parse_formula_dependencies(sheet)
                
    #         neo4j_svc.close()
    #     except Exception as e:
    #         logger.error(f"Lỗi đồng bộ Graph: {str(e)}")

    def _detect_and_create_region(self, ws, sheet_obj):
        """Tự động gom nhóm TAB1, TAB2 dựa trên cấu hình tiêu đề (logic tiệm vàng)"""
        # Đây là nơi anh Vũ định nghĩa: Cứ thấy ô màu Vàng/Cam là bắt đầu một Region mới
        region, _ = ExcelTableRegion.objects.get_or_create(
            sheet=sheet_obj,
            name=f"Main_Region_{sheet_obj.name}",
            defaults={'coordinates': 'A1:Z100', 'region_type': 'FORM'}
        )
        return region

    def _prepare_cell_logic(self, ws, sheet_obj, cell, region):
        """Phân tích sâu từng ô dữ liệu"""
        raw_val = cell.value
        if isinstance(raw_val, (datetime.datetime, datetime.date)):
            raw_val = raw_val.isoformat()

        val_str = str(raw_val).strip() if raw_val is not None else ""
        is_formula = val_str.startswith('=')
        
        # Nhãn thông minh (Lấy ô bên trái hoặc bên trên)
        smart_label = self._get_smart_label(ws, cell)
        
        # Màu sắc (Để nhận diện ô quan trọng)
        bg_color = "FFFFFF"
        if cell.fill and hasattr(cell.fill, 'start_color'):
            bg_color = str(cell.fill.start_color.rgb)

        return DataField(
            sheet=sheet_obj,
            region=region,
            cell_address=cell.coordinate,
            label=smart_label[:255],
            value=val_str,
            formula=val_str if is_formula else "",
            color_code=bg_color,
            is_required=(bg_color in ["FFFF0000", "FFFFC000"]), # Đỏ hoặc Cam là bắt buộc
            metadata={
                'comment': cell.comment.text if cell.comment else "",
                'is_formula': is_formula,
                'bg_color': bg_color
            }
        )

    def _create_knowledge_draft_internal(self, project, field_obj, cell):
        """Tạo bản thảo cho Agent học"""
        content = f"Nghiệp vụ: {field_obj.label}\nVị trí: {field_obj.sheet.name}!{field_obj.cell_address}\n"
        if field_obj.formula:
            content += f"Logic tính toán: {field_obj.formula}\n"
        if field_obj.metadata.get('comment'):
            content += f"Lưu ý nghiệp vụ: {field_obj.metadata['comment']}\n"

        return KnowledgeDraft(
            project=project,
            term=field_obj.label or f"Logic_{field_obj.cell_address}",
            content=content,
            category='LOGIC' if field_obj.formula else 'TERM',
            status='PENDING'
        )

    def _get_smart_label(self, ws, cell):
        """Tìm nhãn văn bản gần nhất (Trái hoặc Trên)"""
        # Thử bên trái
        l_val = ws.cell(row=cell.row, column=max(1, cell.column - 1)).value
        if l_val and isinstance(l_val, str): return l_val.strip()
        # Thử bên trên
        t_val = ws.cell(row=max(1, cell.row - 1), column=cell.column).value
        if t_val and isinstance(t_val, str): return t_val.strip()
        return f"Cell_{cell.coordinate}"
