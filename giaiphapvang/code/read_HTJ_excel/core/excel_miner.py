import openpyxl
import os
from database.models import ExcelSheet, DataGroup, DataField

class ExcelMiner:
    def __init__(self, file_path):
        self.file_path = os.path.abspath(file_path)
        try:
            # data_only=False để lấy được công thức (formula)
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
            # Lấy mã màu để AI biết ô nào là ô quan trọng/nhập liệu
            return str(cell.fill.start_color.index)
        return "N/A"

    def scan_project(self) -> list[ExcelSheet]:
        project_data = []
        print(f"\n{'='*50}")
        print(f"📊 BẮT ĐẦU QUÉT HỆ THỐNG: {os.path.basename(self.file_path)}")
        print(f"{'='*50}")

        for name in self.wb.sheetnames:
            ws = self.wb[name]
            sheet_status = self._detect_status(name)
            
            sheet_obj = ExcelSheet(sheet_name=name, status=sheet_status)
            raw_group = DataGroup(group_name=f"Data_{name}")
            
            # Chuyển sheet thành list để xử lý tiêu đề
            rows = list(ws.iter_rows())
            if not rows:
                continue

            # --- CHIẾN THUẬT NHẬN DIỆN LABEL ---
            # Giả định hàng 1 hoặc hàng chứa dữ liệu đầu tiên là tiêu đề
            headers = {}
            for row in rows[:5]: # Quét 5 hàng đầu để tìm hàng có nhiều chữ nhất làm header
                current_headers = {cell.column: str(cell.value).strip() for cell in row if cell.value is not None}
                if len(current_headers) > len(headers):
                    headers = current_headers

            count_cells = 0
            print(f"\n📂 Đang phân tích Sheet: [{name}]")

            for row in rows:
                for cell in row:
                    if cell.value is not None:
                        val_str = str(cell.value).strip()
                        is_formula = val_str.startswith('=')
                        
                        # --- PHÂN LOẠI THÔNG MINH CHO AI ---
                        f_type = "DATA"
                        
                        # 1. Nhận diện Nút bấm (Actions)
                        # Nếu ô chứa các động từ nghiệp vụ, đánh dấu là ACTION
                        action_keywords = [
                            "PHÂN BỔ", "TÍNH", "LƯU", "GHI", "IN PHIẾU", 
                            "XÓA", "SỬA", "CHỐT", "KIỂM TRA", "TẠO"
                        ]
                        if any(act in val_str.upper() for act in action_keywords) and len(val_str) < 30:
                            f_type = "ACTION"
                        
                        # 2. Nhận diện ô công thức
                        elif is_formula:
                            f_type = "AUTO_CALC"

                        # 3. Lấy Label tương ứng (AI sẽ biết giá trị này thuộc cột nào)
                        col_label = headers.get(cell.column, "Thông tin khác")

                        field_obj = DataField(
                            coord=cell.coordinate,
                            row=cell.row,
                            column=cell.column,
                            label=col_label, 
                            value=val_str if not is_formula else "Hệ thống tự tính",
                            formula=val_str if is_formula else None,
                            color_code=self._get_color(cell),
                            field_type=f_type
                        )
                        
                        raw_group.fields.append(field_obj)
                        count_cells += 1
                        
                        if count_cells <= 3:
                            print(f"   📍 [{f_type}] {cell.coordinate} ({col_label}): {val_str[:20]}")

            if raw_group.fields:
                sheet_obj.groups.append(raw_group)
                project_data.append(sheet_obj)
                print(f"   ✅ Xong [{name}]: Đã lấy {count_cells} thành phần giao diện.")

        print(f"\n{'='*50}")
        print(f"🏁 TỔNG KẾT: Đã bóc tách xong {len(project_data)} Form nghiệp vụ.")
        print(f"{'='*50}\n")
        
        return project_data

    def close(self):
        self.wb.close()