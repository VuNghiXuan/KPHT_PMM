import openpyxl
import datetime
import traceback
from openpyxl.cell.cell import MergedCell
from apps.system_monitor.models import DataType
from .models import ExcelSheet, DataField
from apps.ai_knowledge.models import KnowledgeDraft

class ExcelMinerService:
    def __init__(self):
        self.keywords_dict = {}
        self.important_codes = []
        self.default_dtype = None
        self.formula_dtype = None

    def _prepare_resources(self):
        """Tải cấu hình DataType từ DB"""
        data_types = DataType.objects.all()
        self.keywords_dict = {
            dt.name.lower(): {
                'code': dt.code, 
                'is_important': getattr(dt, 'is_important', False)
            } for dt in data_types
        }
        self.important_codes = [v['code'] for k, v in self.keywords_dict.items() if v['is_important']]
        if not self.important_codes:
            self.important_codes = ['AMOUNT', 'WEIGHT', 'PERSON_NAME', 'BANK_ACCOUNT']

        self.default_dtype, _ = DataType.objects.get_or_create(code='MOCK', defaults={'name': 'Dữ liệu thô'})
        self.formula_dtype, _ = DataType.objects.get_or_create(code='FORMULA', defaults={'name': 'Công thức'})

    def process_project(self, project):
        """Hàm chính: Quét toàn bộ Workbook"""
        self._prepare_resources()
        try:
            wb = openpyxl.load_workbook(project.file_path.path, data_only=False)
            total_sheets = len(wb.sheetnames)

            for index, sheet_name in enumerate(wb.sheetnames):
                ws = wb[sheet_name]
                sheet_obj, _ = ExcelSheet.objects.update_or_create(
                    project=project, name=sheet_name,
                    defaults={'sheet_index': index, 'category': 'TAB_UI'}
                )

                DataField.objects.filter(sheet=sheet_obj).delete()
                fields_to_create = []

                # Giới hạn vùng quét để tối ưu hiệu năng
                for row in ws.iter_rows(max_row=1000, max_col=50):
                    for cell in row:
                        if cell.value is not None or (hasattr(cell, 'comment') and cell.comment):
                            field_obj = self._prepare_cell_logic(ws, sheet_obj, cell)
                            fields_to_create.append(field_obj)
                
                if fields_to_create:
                    DataField.objects.bulk_create(fields_to_create, batch_size=500)
            
            return True, f"Thành công: Đã vét {total_sheets} sheets."
        except Exception:
            return False, traceback.format_exc()

    def _prepare_cell_logic(self, ws, sheet_obj, cell):
        """Phân tích đa tầng: Tọa độ, UI, Logic nghiệp vụ và Tri thức ẩn"""
        from .models import DataField
        
        is_merged = isinstance(cell, MergedCell)
        raw_val = cell.value if not is_merged else None 
        
        # Chuẩn hóa dữ liệu ngày tháng
        if isinstance(raw_val, (datetime.datetime, datetime.date, datetime.time)):
            raw_val = raw_val.isoformat()

        val_str = str(raw_val).strip() if raw_val is not None else ""
        clean_val = " ".join(val_str.lower().split())
        is_formula = val_str.startswith('=')

        # --- 1. THU THẬP NGỮ CẢNH XUNG QUANH ---
        neighbor_left = ws.cell(row=cell.row, column=max(1, cell.column - 1)).value if cell.column > 1 else None
        neighbor_top = ws.cell(row=max(1, cell.row - 1), column=cell.column).value if cell.row > 1 else None
        col_header = ws.cell(row=1, column=cell.column).value or ws.cell(row=2, column=cell.column).value
        
        # Vét tri thức ẩn từ Comment (Cực kỳ quan trọng để AI không ngáo)
        cell_comment = cell.comment.text if hasattr(cell, 'comment') and cell.comment else ""
        # Xác định nhãn hiển thị cho ô này (Ví dụ: "Số tiền chuyển đổi")
        smart_label = self._get_smart_label(ws, cell)

        # --- 2. PHÂN LOẠI BUSINESS LABEL ---
        biz_labels = []
        sources = [clean_val, str(col_header).lower(), str(neighbor_left).lower(), str(neighbor_top).lower(), smart_label.lower()]
        for src in sources:
            if not src or src == 'none': continue
            for kw, info in self.keywords_dict.items():
                if kw in src:
                    code = info['code'] if isinstance(info, dict) else info
                    if code not in biz_labels: biz_labels.append(code)
            if biz_labels: break

        # --- 3. NHẬN DIỆN STYLE & MÀU SẮC (UI RECOGNITION) ---
        bg_color = "00000000"
        if hasattr(cell.fill, 'start_color'):
            bg_color = str(cell.fill.start_color.index) if cell.fill.start_color.type == 'indexed' else str(cell.fill.start_color.rgb)
        
        is_bold = cell.font.bold if hasattr(cell.font, 'bold') else False
        
        # Phân loại loại ô dựa trên Style
        ui_type = "DATA_CELL"
        if is_bold and bg_color not in ["00000000", "FFFFFFFF", "N/A"]: 
            ui_type = "GRID_HEADER"
        elif bg_color not in ["00000000", "FFFFFFFF", "N/A"] and 0 < len(val_str) < 30: 
            ui_type = "UI_BUTTON"

        # --- 4. PHÂN NHÓM CHỨC NĂNG (FUNCTIONAL GROUP) ---
        func_group = "GENERAL_INFO"
        if ui_type == "UI_BUTTON": 
            func_group = "ACTION_TRIGGER"
        elif ui_type == "GRID_HEADER": 
            func_group = "SECTION_HEADER"
        elif any(label in self.important_codes for label in biz_labels) or is_formula:
            # Nếu là ô quan trọng (Tiền, Trọng lượng) hoặc có Công thức -> Đưa vào nhóm kiểm soát
            func_group = "CRITICAL_INPUT_VALIDATION"
        elif biz_labels: 
            func_group = "DATA_INPUT_FIELD"

        # --- 5. ĐÓNG GÓI DỮ LIỆU ---
        return DataField(
            sheet=sheet_obj, 
            cell_address=cell.coordinate,
            label=biz_labels[0] if biz_labels else None,
            value=val_str, 
            raw_value=raw_val if not is_formula else None,
            formula=val_str if is_formula else "",
            color_code=bg_color,
            field_type=self.formula_dtype if is_formula else self.default_dtype,
            metadata={
                'ui_context': {
                    'type': ui_type, 
                    'functional_group': func_group, 
                    'coordinate': cell.coordinate,
                    'comment': cell_comment # Tri thức ẩn bổ sung
                },
                'area_context': {
                    'neighbor_left': str(neighbor_left), 
                    'neighbor_top': str(neighbor_top), 
                    'parent_col_title': str(col_header),
                    'smart_label': smart_label # Tên thực tế của ô trên form
                },
                'business_context': {
                    'labels': biz_labels, 
                    'is_formula': is_formula,
                    'is_required': bg_color in ["FFFF0000", "FFFFC000"] # Giả định đỏ/cam là bắt buộc
                }
            }
        )
    
    def _get_smart_label(self, ws, cell):
        """Tìm nhãn văn bản gần nhất phía trên hoặc bên trái để định danh ô"""
        # 1. Thử lấy nhãn bên trái
        left_val = ws.cell(row=cell.row, column=max(1, cell.column - 1)).value
        if left_val and isinstance(left_val, str) and len(left_val) < 50:
            return str(left_val).strip()
        
        # 2. Thử lấy nhãn phía trên
        top_val = ws.cell(row=max(1, cell.row - 1), column=cell.column).value
        if top_val and isinstance(top_val, str) and len(top_val) < 50:
            return str(top_val).strip()
            
        return ""