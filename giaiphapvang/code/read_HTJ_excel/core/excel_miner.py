import openpyxl
import os
import json
from database.models import ExcelSheet, DataGroup, DataField
from config import Config

class ExcelMiner:
    def __init__(self, file_path):
        self.file_path = os.path.abspath(file_path)
        try:
            # Lấy công thức thô (data_only=False)
            self.wb = openpyxl.load_workbook(self.file_path, data_only=False)
            # Lấy giá trị đã tính toán (data_only=True) để đối soát
            self.wb_val = openpyxl.load_workbook(self.file_path, data_only=True)
        except Exception as e:
            raise Exception(f"Lỗi đọc file: {e}")

    def _get_color(self, cell) -> str:
        if cell.fill and hasattr(cell.fill, 'start_color'):
            # Trả về mã màu ARGB (ví dụ: FFFFFF00 là màu vàng)
            return str(cell.fill.start_color.index)
        return "N/A"

    def scan_project(self) -> list:
        project_data = []
        knowledge_backup = [] # File JSON "xác" file Excel như anh muốn

        for name in self.wb.sheetnames:
            ws = self.wb[name]
            ws_val = self.wb_val[name]
            
            sheet_obj = ExcelSheet(sheet_name=name, status="SCANNING")
            raw_group = DataGroup(group_name=f"Full_Data_{name}")
            
            print(f"🔍 Đang 'vét cạn' dữ liệu tại Sheet: [{name}]")

            # 1. QUÉT TOÀN BỘ Ô CÓ DỮ LIỆU HOẶC COMMENT
            # Dùng ws.calculate_dimension() để lấy vùng hoạt động thực sự
            for row in ws.iter_rows():
                for cell in row:
                    # Lấy giá trị thực tế sau khi tính (nếu là công thức)
                    real_val = ws_val[cell.coordinate].value
                    # Lấy công thức thô
                    raw_val = cell.value
                    
                    # Điều kiện vét: Có giá trị HOẶC có comment HOẶC có màu nền
                    has_comment = cell.comment is not None
                    has_color = self._get_color(cell) != "00000000" and self._get_color(cell) != "N/A"
                    
                    if raw_val is not None or has_comment or has_color:
                        val_str = str(raw_val).strip()
                        is_formula = str(raw_val).startswith('=')
                        
                        # --- LOGIC NHẬN DIỆN CHI TIẾT ---
                        f_type = "DATA"
                        
                        # Nhận diện Button/Action
                        action_keywords = Config.ACTION_KEYWORDS
                        if any(k in val_str.upper() for k in action_keywords) and len(val_str) < 20:
                            f_type = "UI_BUTTON"
                        
                        # Nhận diện Header của Grid (Thường in đậm hoặc có màu nền khác biệt)
                        is_bold = cell.font.bold if cell.font else False
                        if is_bold and not is_formula:
                            f_type = "GRID_HEADER"

                        # Thu thập mọi "vảy" thông tin
                        field_info = {
                            "coord": cell.coordinate,
                            "row": cell.row,
                            "col": cell.column,
                            "value": str(real_val) if real_val is not None else "",
                            "formula": val_str if is_formula else None,
                            "comment": cell.comment.text.strip() if has_comment else None,
                            "color": self._get_color(cell),
                            "is_bold": is_bold,
                            "type": f_type,
                            "sheet": name
                        }

                        # Lưu vào Object để nạp DB
                        field_obj = DataField(
                            coord=field_info["coord"],
                            row=field_info["row"],
                            column=field_info["col"],
                            label=f_type, # AI sẽ dùng thông tin này để gán nhãn lại
                            value=field_info["value"],
                            formula=field_info["formula"],
                            color_code=field_info["color"],
                            field_type=f_type
                        )
                        
                        # Bổ sung ghi chú vào label nếu có comment để AI dễ đọc
                        if field_info["comment"]:
                            field_obj.label = f"{f_type} (NOTE: {field_info['comment']})"

                        raw_group.fields.append(field_obj)
                        knowledge_backup.append(field_info)

            if raw_group.fields:
                sheet_obj.groups.append(raw_group)
                project_data.append(sheet_obj)

        # 2. XUẤT FILE JSON BACKUP (KNOWLEDGE BASE)
        self._save_backup(knowledge_backup)
        
        return project_data

    def _save_backup(self, data):
        backup_path = "knowledge_backup.json"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"💾 Đã sao lưu 'gen' hệ thống vào: {backup_path}")

    def close(self):
        self.wb.close()
        self.wb_val.close()