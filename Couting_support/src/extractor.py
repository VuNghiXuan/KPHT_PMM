# ==============================================================================
# Đường dẫn: Couting_support/src/extractor.py
# Mục đích: Backend xử lý đọc file, tích hợp thuật toán Cosine Similarity / SequenceMatcher
#           để so khớp tiêu đề cột thông minh, phân tách chính xác Số lô và Số hóa đơn.
# ==============================================================================

import os
import re
import json
import difflib
import cv2
import numpy as np
import easyocr
import pandas as pd
from pdfplumber import open as open_pdf
import xml.etree.ElementTree as ET

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")

def load_config():
    """Hàm tải cấu hình từ điển config.json."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"target_columns": [], "column_synonyms": {}}

print("Đang khởi tạo mô hình EasyOCR (Tiếng Việt & Tiếng Anh)...")
reader = easyocr.Reader(['vi', 'en'], gpu=False)
print("Đã tải xong EasyOCR.")


class InvoiceExtractor:
    """
    Class xử lý trích xuất dữ liệu, tích hợp thuật toán đo độ tương tự chuỗi (Cosine/Matcher)
    để map chính xác tiêu đề cột từ file Excel/Chứng từ.
    """
    def __init__(self):
        config = load_config()
        self.target_columns = config.get("target_columns", [])
        self.synonyms = config.get("column_synonyms", {})

    def find_best_match_column(self, header_cell_text):
        """
        Sử dụng thuật toán tương tự Cosine Similarity (SequenceMatcher) 
        để tìm cột mục tiêu có độ khớp cao nhất từ từ điển synonyms.
        """
        if not header_cell_text or pd.isna(header_cell_text):
            return None
            
        clean_cell = str(header_cell_text).strip().lower()
        best_match_col = None
        highest_score = 0.0

        for target_col, syn_list in self.synonyms.items():
            for syn in syn_list:
                clean_syn = syn.lower()
                # Tính tỷ lệ tương đồng chuỗi (0.0 đến 1.0)
                score = difflib.SequenceMatcher(None, clean_cell, clean_syn).ratio()
                
                # Ưu tiên tuyệt đối nếu chứa từ khóa hoặc khớp cao hơn ngưỡng 0.8
                if clean_cell == clean_syn or clean_syn in clean_cell:
                    score = 1.0

                if score > highest_score:
                    highest_score = score
                    best_match_col = target_col

        # Ngưỡng chấp nhận độ tương đồng >= 0.75
        if highest_score >= 0.75:
            return best_match_col
        return None

    def extract_rows_from_excel_multisheet(self, excel_path):
        """
        Đọc file Excel qua tất cả các sheet, sử dụng thuật toán thông minh để map cột
        và phân tách rõ ràng giữa 'Số lô' và 'Số hóa đơn'.
        """
        extracted_rows = []
        try:
            excel_file = pd.ExcelFile(excel_path)
            
            for sheet_name in excel_file.sheet_names:
                df_sheet = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                if df_sheet.empty:
                    continue

                df_sheet = df_sheet.dropna(how='all').dropna(how='all', axis=1)
                header_idx = -1
                column_mapping = {}

                # Quét tìm dòng Header sử dụng thuật toán matching
                for idx, row in df_sheet.iterrows():
                    matches = 0
                    temp_map = {}
                    for col_idx, cell_val in enumerate(row.values):
                        if pd.isna(cell_val):
                            continue
                        matched_col = self.find_best_match_column(cell_val)
                        if matched_col and matched_col not in temp_map.values():
                            temp_map[col_idx] = matched_col
                            matches += 1

                    if matches >= 3:
                        header_idx = idx
                        column_mapping = temp_map
                        break

                # Bóc tách dữ liệu dòng bên dưới Header
                if header_idx != -1 and column_mapping:
                    df_data = df_sheet.iloc[header_idx + 1:]
                    for _, row in df_data.iterrows():
                        row_data = {col: "" for col in self.target_columns}
                        has_data = False
                        
                        for col_idx, target_col in column_mapping.items():
                            val = row.values[col_idx] if col_idx < len(row.values) else None
                            if pd.notna(val):
                                row_data[target_col] = str(val).strip()
                                has_data = True
                        
                        if has_data:
                            # Đảm bảo nhận diện Số lô nếu có chứa từ khóa lô hoặc mã xịt, tránh gán nhầm sang Số hóa đơn
                            for val_cell in row.values:
                                if pd.notna(val_cell):
                                    v_str = str(val_cell).strip()
                                    if "xitrang" in v_str.lower() or "lô" in v_str.lower() or "-" in v_str and len(v_str) > 6:
                                        if not row_data.get("Số lô"):
                                            row_data["Số lô"] = v_str

                            extracted_rows.append(row_data)

        except Exception as e:
            print(f"Lỗi đọc Excel multi-sheet: {e}")
            
        return extracted_rows

    def extract_folder(self, input_folder="input_files/"):
        """Duyệt thư mục input_files và trả về DataFrame chuẩn hóa."""
        all_extracted_rows = []
        if not os.path.exists(input_folder):
            os.makedirs(input_folder)
            return pd.DataFrame(columns=self.target_columns)

        for file_name in os.listdir(input_folder):
            if file_name.startswith("~$"):
                continue
            file_path = os.path.join(input_folder, file_name)
            if not os.path.isfile(file_path):
                continue

            ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
            if ext in ['xlsx', 'xls']:
                rows = self.extract_rows_from_excel_multisheet(file_path)
                all_extracted_rows.extend(rows)

        if not all_extracted_rows:
            return pd.DataFrame(columns=self.target_columns)

        df_final = pd.DataFrame(all_extracted_rows, columns=self.target_columns)
        df_final["STT"] = range(1, len(df_final) + 1)
        return df_final


def extract_invoice_data(input_folder="input_files/"):
    """Hàm giao tiếp chính giữa UI và Backend."""
    extractor = InvoiceExtractor()
    return extractor.extract_folder(input_folder)