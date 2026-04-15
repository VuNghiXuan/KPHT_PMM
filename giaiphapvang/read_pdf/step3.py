import pdfplumber
import os
import re
import pandas as pd

def read_pdf_file_pdfplumber(file_path):
    """
    Trích xuất toàn bộ văn bản từ một file PDF và phân tích dữ liệu Phân kim.
    """
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại đường dẫn: {file_path}")
        return

    full_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Sử dụng strip() để loại bỏ khoảng trắng dư thừa ở đầu/cuối mỗi dòng 
                # trước khi nối, giúp văn bản thô dễ phân tích hơn
                full_text += page.extract_text().strip() + "\n"
        
        print(f"--- Đã trích xuất văn bản thô từ {len(pdf.pages)} trang ---")
        print(f"--- Dữ liệu thô ---\n")
        print(full_text)
        print("------------------------------------------------")
        
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình đọc file PDF: {e}")
        return

    data_list = analyze_gold_data(full_text)
    
    if data_list:
        output_file = file_path.replace(".pdf", "_analyzed.xlsx")
        export_to_excel(data_list, output_file)
    else:
        print("\n--- Không tìm thấy dữ liệu Dẻ vàng nào để phân tích. ---")


def analyze_gold_data(text):
    """
    Sử dụng Regex để phân tích cấu trúc lặp lại của các mục Dẻ số và trích xuất 
    thông tin chi tiết theo cấu trúc file Excel mục tiêu, bao gồm cả dòng "Tổng".
    """
    # Khai báo một Regex linh hoạt hơn để khớp với số thập phân (có thể là dấu phẩy hoặc dấu chấm)
    # Tuy nhiên, dựa trên các mẫu trước, ta giữ nguyên dấu chấm để đảm bảo tính nhất quán (dễ chuẩn hóa)
    DECIMAL_PATTERN = r'\d+\.\d+' 
    
    # 1. Trích xuất thông tin chung (Header Metadata)
    pk_match = re.search(r'DỊCH VỤ PHÂN KIM - TRAO ĐỔI DẺ\s*\((PK\d+)\)', text)
    pk_code = pk_match.group(1) if pk_match else "N/A"
    
    # Regex để tìm và nhóm toàn bộ thông tin của mỗi "Dẻ số X"
    # Dùng re.DOTALL để khớp với ký tự xuống dòng
    # Dùng \s* để khớp với 0 hoặc nhiều khoảng trắng (tăng linh hoạt)
    pattern = re.compile(r'(Dẻ số\s*\d+.*?)(?=Dẻ số\s*\d+|DỊCH VỤ PHÂN KIM|$)', re.DOTALL)
    
    data_records = []
    
    # 2. Trích xuất dữ liệu chi tiết theo từng Dẻ số
    for match in pattern.finditer(text):
        dinh_danh_text = match.group(0)
        
        # Khởi tạo record
        record = {}

        # Trích xuất các trường dữ liệu chi tiết
        try:
            # Dẻ số
            record["Dẻ số"] = re.search(r'Dẻ số\s*(\d+)', dinh_danh_text).group(1)
            
            # 1. Trọng lượng (chỉ) - Vàng đưa (Cột Trọng lượng (chỉ) đầu tiên) & 5. Tuổi vàng
            # Thêm \s* để linh hoạt hơn về khoảng trắng
            vang_dua_match = re.search(r'Vàng khách đưa:\s*(' + DECIMAL_PATTERN + r')\s*chỉ.*?Tuổi vàng:\s*(' + DECIMAL_PATTERN + r')%', dinh_danh_text, re.DOTALL)
            record["Trọng lượng (chỉ)"] = vang_dua_match.group(1) if vang_dua_match else "N/A"
            record["Tuổi vàng"] = vang_dua_match.group(2) if vang_dua_match else "N/A"
            
            # 2. Phổ 1, Phổ 2
            pho_pk_match = re.search(r'Phổ:\s*(' + DECIMAL_PATTERN + r')%\s*,\s*(' + DECIMAL_PATTERN + r')%', dinh_danh_text, re.DOTALL)
            record["Phổ 1"] = pho_pk_match.group(1) if pho_pk_match else "0.00"
            record["Phổ 2"] = pho_pk_match.group(2) if pho_pk_match else "0.00"
            record["Phổ 3"] = "0.00" # Mặc định theo mẫu Excel
            record["Phổ 4"] = "0.00" # Mặc định theo mẫu Excel
            
            # 3. Trọng lượng (chỉ) - TL Tính
            tl_tinh_match = re.search(r'TL Tính:\s*(' + DECIMAL_PATTERN + r')\s*chỉ', dinh_danh_text, re.DOTALL)
            record["Trọng lượng (chỉ) - TL Tính"] = tl_tinh_match.group(1) if tl_tinh_match else "N/A"

            # 4. Quy 9999
            quy9999_match = re.search(r'Quy 9999\s*(' + DECIMAL_PATTERN + r')', dinh_danh_text, re.DOTALL)
            record["Quy 9999"] = quy9999_match.group(1) if quy9999_match else "N/A"

            # 6. Lai PK và Quy 10 (chỉ)
            lai_quy_match = re.search(r'Lai PK:\s*(' + DECIMAL_PATTERN + r').*?Quy 10:\s*(' + DECIMAL_PATTERN + r')\s*chỉ', dinh_danh_text, re.DOTALL)
            record["Lai PK"] = lai_quy_match.group(1) if lai_quy_match else "N/A"
            record["Quy 10 (chỉ)"] = lai_quy_match.group(2) if lai_quy_match else "N/A"
            
            # 7. Trọng lượng (chỉ) - Trả (Lấy giá trị Trả vàng)
            # Trả vàng là giá trị số thập phân thứ hai sau 'TL Tính: <val1> chỉ'
            tra_vang_match = re.search(r'TL Tính:\s*' + DECIMAL_PATTERN + r'\s*chỉ.*?(' + DECIMAL_PATTERN + r')\s*chỉ', dinh_danh_text, re.DOTALL)
            record["Trọng lượng (chỉ) - Trả"] = tra_vang_match.group(1) if tra_vang_match else "0" 

            # 8. Phổ 1-4, Tuổi vàng Dẻ trả khách (Mặc định 0.00/0 theo mẫu)
            record["Phổ 1 - Trả khách"] = "0"
            record["Phổ 2 - Trả khách"] = "0"
            record["Phổ 3 - Trả khách"] = "0"
            record["Phổ 4 - Trả khách"] = "0"
            record["Tuổi vàng - Trả"] = "0.00"
            
            # 9. Cân lại
            can_lai_match = re.search(r'Cân lại:\s*(' + DECIMAL_PATTERN + r')\s*chỉ', dinh_danh_text, re.DOTALL)
            record["Cân lại"] = can_lai_match.group(1) if can_lai_match else "0"
            
            # 10. Thành tiền *95
            tt_tien_match = re.search(r'TT Tiền\*95\s*(' + DECIMAL_PATTERN + r')\s*x\s*(\d+)', dinh_danh_text, re.DOTALL)
            # Lấy giá trị thứ hai (0)
            record["Thành tiền *95"] = tt_tien_match.group(2) if tt_tien_match else "0"

        except AttributeError as e:
            # Nếu không trích xuất được trường bắt buộc nào đó, sẽ in cảnh báo
            print(f"Cảnh báo: Không tìm thấy đủ trường dữ liệu cho Dẻ số {record.get('Dẻ số', 'N/A')} - Lỗi: {e}")
            continue

        data_records.append(record)
    
    # 3. Trích xuất và thêm dòng "Tổng" (nếu có)
    # Tổng TL nhận khách
    total_tl_match = re.search(r'Tổng TL nhận khách:\s*(' + DECIMAL_PATTERN + r')\s*chỉ', text)
    total_tl_receive = total_tl_match.group(1) if total_tl_match else None
    
    if total_tl_receive:
        # Tổng Quy 10 được trích xuất nếu có
        total_quy_match = re.search(r'Tổng.*?Quy 10:\s*(' + DECIMAL_PATTERN + r')\s*chỉ', text)
        
        total_row = {
            "Dẻ số": "Tổng",
            "Trọng lượng (chỉ)": total_tl_receive,
            "Phổ 1": "0.00", "Phổ 2": "0.00", "Phổ 3": "0.00", "Phổ 4": "0.00", 
            "Tuổi vàng": "N/A",
            "Trọng lượng (chỉ) - TL Tính": "N/A",
            "Quy 9999": "N/A", "Lai PK": "N/A", 
            "Quy 10 (chỉ)": total_quy_match.group(1) if total_quy_match else "N/A",

            "Trọng lượng (chỉ) - Trả": "0", "Phổ 1 - Trả khách": "0", "Phổ 2 - Trả khách": "0",
            "Phổ 3 - Trả khách": "0", "Phổ 4 - Trả khách": "0", "Tuổi vàng - Trả": "0.00",
            "Cân lại": "0", "Thành tiền *95": "0"
        }
        data_records.append(total_row)

    return data_records

def export_to_excel(data_list, output_file):
    """
    Chuyển List of Dictionaries sang DataFrame và xuất ra file Excel.
    Cấu trúc cột được sắp xếp lại theo yêu cầu.
    """
    try:
        df = pd.DataFrame(data_list)
        
        # Sắp xếp thứ tự cột theo yêu cầu của bạn (như trong hình ảnh Excel)
        final_columns_order = [
            "Dẻ số", 
            
            # Thông tin đổi dẻ
            "Trọng lượng (chỉ)", 
            "Phổ 1", 
            "Phổ 2", 
            "Phổ 3", 
            "Phổ 4", 
            "Tuổi vàng",
            "Trọng lượng (chỉ) - TL Tính",
            "Quy 9999", 
            "Lai PK", 
            "Quy 10 (chỉ)", 
            
            # Dẻ trả khách
            "Trọng lượng (chỉ) - Trả", 
            "Phổ 1 - Trả khách", 
            "Phổ 2 - Trả khách", 
            "Phổ 3 - Trả khách", 
            "Phổ 4 - Trả khách", 
            "Tuổi vàng - Trả", 
            "Cân lại", 
            "Thành tiền *95"
        ]

        # Lọc các cột hiện có trong DataFrame để tránh lỗi KeyError
        final_columns_order = [col for col in final_columns_order if col in df.columns]
        df = df[final_columns_order]
        
        # Lưu ra file Excel
        df.to_excel(output_file, index=False)
        print(f"\n--- Đã phân tích và lưu dữ liệu thành công vào file: {output_file} ---")
        
    except ImportError as e:
        print(f"\n!!! LỖI QUAN TRỌNG: Không tìm thấy module '{e.name}'")
        print("Để xuất file Excel (.xlsx), bạn cần cài đặt thư viện hỗ trợ:")
        print("   >>> pip install openpyxl")
    except Exception as e:
        print(f"Lỗi khi xuất file Excel: {e}")


# --- CÁCH SỬ DỤNG ---
# Thay thế 'your_document.pdf' bằng đường dẫn file PDF thực tế của bạn
pdf_file_path = r'D:\ThanhVu\kpht\GiaiPhapVang\read_pdf\file\input\de.pdf' 

read_pdf_file_pdfplumber(pdf_file_path)
