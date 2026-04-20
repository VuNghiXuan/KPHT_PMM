import openpyxl
import os
from database.models import ExcelSheet, DataGroup, DataField

class ExcelMiner:
    def __init__(self, file_path):
        self.file_path = os.path.abspath(file_path)
        try:
            self.wb = openpyxl.load_workbook(self.file_path, data_only=False)
        except Exception as e:
            raise Exception(f"Lỗi đọc file: {e}")

    def _detect_status(self, name: str) -> str:
        name_upper = name.upper()
        for status in ["DONE", "EDITING", "PENDING", "REVIEW"]:
            if status in name_upper: return status
        return "UNKNOWN"

    def _get_color(self, cell) -> str:
        if cell.fill and hasattr(cell.fill, 'start_color'):
            return str(cell.fill.start_color.index)
        return "N/A"

    def scan_project(self) -> list[ExcelSheet]:
        project_data = []
        print(f"\n{'='*50}")
        print(f"📊 BẮT ĐẦU QUÉT FILE: {os.path.basename(self.file_path)}")
        print(f"{'='*50}")

        for name in self.wb.sheetnames:
            ws = self.wb[name]
            sheet_status = self._detect_status(name)
            
            # Tạo object Sheet mới cho mỗi vòng lặp
            sheet_obj = ExcelSheet(sheet_name=name, status=sheet_status)
            
            # Group chứa dữ liệu của sheet này
            raw_group = DataGroup(group_name=f"Data_{name}")
            
            count_cells = 0
            print(f"\n📂 Đang đọc Sheet: [{name}] | Trạng thái: {sheet_status}")

            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:  
                        val_str = str(cell.value)
                        is_formula = val_str.startswith('=')
                        
                        field_obj = DataField(
                            coord=cell.coordinate,
                            row=cell.row,
                            column=cell.column,
                            label=None,
                            value=val_str if not is_formula else "Calculated",
                            formula=val_str if is_formula else None,
                            color_code=self._get_color(cell),
                            field_type="AUTO_CALC" if is_formula else "DATA"
                        )
                        raw_group.fields.append(field_obj)
                        count_cells += 1
                        
                        # In thử 3 ô đầu tiên của mỗi sheet để kiểm tra
                        if count_cells <= 3:
                            print(f"   📍 Tìm thấy: {cell.coordinate} -> Content: {val_str[:30]}...")

            if raw_group.fields:
                sheet_obj.groups.append(raw_group)
                project_data.append(sheet_obj)
                print(f"   ✅ Hoàn tất sheet [{name}]: Đã lấy {count_cells} ô dữ liệu.")
            else:
                print(f"   ⚠️ Sheet [{name}] rỗng, bỏ qua.")

        print(f"\n{'='*50}")
        print(f"🏁 TỔNG KẾT: Đã hốt xong {len(project_data)} sheets.")
        print(f"{'='*50}\n")
        
        return project_data

    def close(self):
        self.wb.close()