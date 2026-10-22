# ==============================================================================
# Đường dẫn: Couting_support/src/reconciler.py
# Mục đích: Module Backend xử lý đối chiếu chéo dữ liệu giữa hệ thống nội bộ 
#           và file đối tác. Tích hợp thuật toán so khớp chuỗi (SequenceMatcher/Cosine)
#           trên toàn bộ dòng, kèm hàm làm sạch số liệu an toàn để tránh lỗi ValueError.
# Class chính: InvoiceReconciler
# Các hàm chính: 
#   - safe_to_float(): Chuyển đổi an toàn chuỗi sang kiểu số thực (float).
#   - load_external_file_multisheet(): Đọc và bóc tách file đối tác đa sheet.
#   - compare_datasets_with_cosine(): Thực hiện so khớp 2 lớp an toàn.
#   - export_report_to_excel(): Xuất kết quả đối chiếu ra file Excel.
# ==============================================================================

import os
import re
import difflib
import pandas as pd
from src.extractor import InvoiceExtractor

class InvoiceReconciler:
    """
    Lớp xử lý đối chiếu nâng cao: Kế thừa cơ chế đọc file của Tab 2, 
    áp dụng thuật toán tương đồng chuỗi và làm sạch dữ liệu số an toàn.
    """
    def __init__(self, system_df):
        self.system_df = system_df
        self.extractor = InvoiceExtractor()

    def safe_to_float(self, val):
        """
        Hàm phụ trợ: Chuyển đổi an toàn mọi giá trị sang kiểu float.
        Loại bỏ các ký tự chữ cái, khoảng trắng, dấu chấm lửng (....) hoặc chuỗi rác.
        Trả về 0.0 nếu không thể ép kiểu sang số.
        """
        if pd.isna(val) or val is None:
            return 0.0
        
        val_str = str(val).strip()
        # Nếu chuỗi chứa các từ khóa văn bản (như 'Ngày...', 'Tháng...') thì trả về 0.0 ngay
        if any(char.isalpha() for char in val_str) or "..." in val_str or "—" in val_str:
            return 0.0

        # Giữ lại số, dấu chấm phân cách thập phân và dấu âm
        cleaned = re.sub(r'[^0-9.-]', '', val_str.replace(',', ''))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    def load_external_file_multisheet(self, file_path):
        """
        Đọc TẤT CẢ các sheet, quét used_range và chuẩn hóa file đối tác 
        thành DataFrame kèm theo thông tin vết (Sheet, Dòng).
        """
        try:
            ext = file_path.lower().split('.')[-1]
            if ext not in ['xlsx', 'xls', 'csv']:
                return None, "Định dạng file không hỗ trợ (chỉ nhận Excel, CSV)."

            if ext == 'csv':
                df_ext = pd.read_csv(file_path)
                df_ext['Sheet_Source'] = 'CSV_Root'
                df_ext['Row_Source'] = range(1, len(df_ext) + 1)
                return df_ext, "Thành công"

            excel_file = pd.ExcelFile(file_path)
            all_rows_with_meta = []

            for sheet_name in excel_file.sheet_names:
                df_sheet = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                if df_sheet.empty:
                    continue

                df_sheet = df_sheet.dropna(how='all').dropna(how='all', axis=1)
                header_idx = -1
                column_mapping = {}

                for idx, row in df_sheet.iterrows():
                    matches = 0
                    temp_map = {}
                    for col_idx, cell_val in enumerate(row.values):
                        if pd.isna(cell_val):
                            continue
                        matched = self.extractor.find_best_match_column(cell_val)
                        if matched and matched not in temp_map.values():
                            temp_map[col_idx] = matched
                            matches += 1

                    if matches >= 2:
                        header_idx = idx
                        column_mapping = temp_map
                        break

                if header_idx != -1 and column_mapping:
                    df_data = df_sheet.iloc[header_idx + 1:]
                    for r_idx, row in df_data.iterrows():
                        row_data = {col: "" for col in self.extractor.target_columns}
                        has_data = False
                        
                        for col_idx, target_col in column_mapping.items():
                            val = row.values[col_idx] if col_idx < len(row.values) else None
                            if pd.notna(val):
                                row_data[target_col] = str(val).strip()
                                has_data = True

                        if has_data:
                            row_data['Sheet_Source'] = sheet_name
                            row_data['Row_Source'] = r_idx + 1
                            all_rows_with_meta.append(row_data)

            if not all_rows_with_meta:
                return None, "Không tìm thấy dữ liệu hợp lệ hoặc không khớp tiêu đề trong file đối tác."

            df_final_ext = pd.DataFrame(all_rows_with_meta)
            return df_final_ext, "Thành công"

        except Exception as e:
            return None, f"Lỗi đọc file đối tác: {str(e)}"

    def compute_row_similarity_text(self, row):
        """
        Gộp toàn bộ dữ liệu của một dòng thành một chuỗi văn bản đại diện 
        để tính toán tỷ lệ tương đồng.
        """
        text_parts = [str(val) for val in row.values if pd.notna(val) and str(val).strip() != '' and not str(val).startswith('Sheet_') and not str(val).startswith('Row_')]
        return " ".join(text_parts)

    def compare_datasets_with_cosine(self, external_df):
        """
        Thực hiện đối chiếu 2 lớp an toàn (Khớp mã cứng & Khớp mềm Cosine),
        sử dụng hàm safe_to_float để tránh hoàn toàn lỗi định dạng chuỗi sang số.
        """
        if self.system_df is None or self.system_df.empty:
            return None, "Dữ liệu hệ thống nội bộ đang trống."

        if external_df is None or external_df.empty:
            return None, "Dữ liệu file đối tác trống."

        sys_df = self.system_df.copy()
        ext_df = external_df.copy()

        if 'Sheet_Source' not in sys_df.columns:
            sys_df['Sheet_Source'] = 'Nội bộ (Tab 2)'
            sys_df['Row_Source'] = range(1, len(sys_df) + 1)

        comparison_results = []

        for ext_idx, ext_row in ext_df.iterrows():
            ext_key = str(ext_row.get('Mã SP', '') or ext_row.get('Mã vạch', '')).strip().upper()
            ext_text = self.compute_row_similarity_text(ext_row)
            
            best_match_sys = None
            max_score = 0.0
            match_type = "Không khớp"

            for sys_idx, sys_row in sys_df.iterrows():
                sys_key = str(sys_row.get('Mã SP', '') or sys_row.get('Mã vạch', '')).strip().upper()
                if ext_key and sys_key and ext_key == sys_key:
                    best_match_sys = sys_row
                    max_score = 1.0
                    match_type = "Khớp mã 100%"
                    break

            if max_score < 1.0:
                for sys_idx, sys_row in sys_df.iterrows():
                    sys_text = self.compute_row_similarity_text(sys_row)
                    score = difflib.SequenceMatcher(None, ext_text, sys_text).ratio()
                    if score > max_score:
                        max_score = score
                        best_match_sys = sys_row
                        match_type = "Khớp tương đồng (Cosine)"

            status = "Khớp"
            notes = []

            if max_score < 0.45 or best_match_sys is None:
                status = "Chỉ có ở Đối tác"
                match_type = "Không tìm thấy"
                max_score = 0.0
            else:
                # Sử dụng safe_to_float để ép kiểu an toàn tuyệt đối, loại bỏ hoàn toàn lỗi ValueError
                w_sys = self.safe_to_float(best_match_sys.get('Tổng cân', 0))
                w_ext = self.safe_to_float(ext_row.get('Tổng cân', 0))
                if w_sys > 0 and w_ext > 0 and abs(w_sys - w_ext) > 0.001:
                    status = "Lệch dữ liệu"
                    notes.append(f"Tổng cân lệch (Kho: {w_sys} vs Đối tác: {w_ext})")

                m_sys = self.safe_to_float(best_match_sys.get('TỔNG GIÁ THÀNH', 0))
                m_ext = self.safe_to_float(ext_row.get('TỔNG GIÁ THÀNH', 0))
                if m_sys > 0 and m_ext > 0 and abs(m_sys - m_ext) > 1.0:
                    status = "Lệch dữ liệu"
                    notes.append(f"Giá thành lệch (Kho: {m_sys} vs Đối tác: {m_ext})")

            comparison_results.append({
                "Nguồn Nội Bộ": f"{best_match_sys.get('Sheet_Source', 'Nội bộ')} - Dòng {best_match_sys.get('Row_Source', '')}" if best_match_sys is not None else "-",
                "Nguồn Đối Tác": f"{ext_row.get('Sheet_Source', 'Sheet1')} - Dòng {ext_row.get('Row_Source', ext_idx+1)}",
                "Mã SP Nội Bộ": best_match_sys.get('Mã SP', '-') if best_match_sys is not None else "-",
                "Mã SP Đối Tác": ext_row.get('Mã SP', '-') or ext_row.get('Mã vạch', '-'),
                "Tỷ lệ Khớp (%)": round(max_score * 100, 2),
                "Phương thức Khớp": match_type,
                "Trạng thái": status,
                "Chi tiết chênh lệch": "; ".join(notes) if notes else "Bình thường"
            })

        df_report = pd.DataFrame(comparison_results)
        return df_report, "Đối chiếu thành công"

    def export_report_to_excel(self, df_report, output_dir="output_excel/"):
        """
        Xuất bảng kết quả đối chiếu ra file Excel và lưu vào thư mục output_excel/.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        file_path = os.path.join(output_dir, "Bao_Cao_Doi_Chieu_Kho.xlsx")
        try:
            df_report.to_excel(file_path, index=False)
            return file_path, "Xuất file Excel thành công!"
        except Exception as e:
            return None, f"Lỗi xuất file: {str(e)}"