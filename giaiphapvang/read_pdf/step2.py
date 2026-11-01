import pdfplumber
import os
import re
import pandas as pd

def read_pdf_file_pdfplumber(file_path):
    """
    Trích xuất toàn bộ văn bản từ một file PDF và phân tích dữ liệu Phân kim.

    Args:
        file_path (str): Đường dẫn đến file PDF cần đọc.
    """
    # Kiểm tra sự tồn tại của file
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại đường dẫn: {file_path}")
        return

    full_text = ""
    try:
        # 1. Mở file PDF và trích xuất toàn bộ văn bản
        with pdfplumber.open(file_path) as pdf:
            # Lặp qua từng trang, trích xuất văn bản thô
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
        
        print(f"--- Đã trích xuất văn bản thô từ {len(pdf.pages)} trang ---")
        
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình đọc file PDF: {e}")
        return

    # 2. Phân tích dữ liệu từ văn bản thô
    data_list = analyze_gold_data(full_text)
    
    # 3. Xuất ra file Excel
    if data_list:
        output_file = file_path.replace(".pdf", "_analyzed.xlsx")
        export_to_excel(data_list, output_file)
        # Thông báo thành công chỉ khi không có lỗi trong hàm export_to_excel
    else:
        print("\n--- Không tìm thấy dữ liệu Dẻ vàng nào để phân tích. ---")


def analyze_gold_data(text):
    """
    Sử dụng Regex để phân tích cấu trúc lặp lại của các mục Dẻ số và trích xuất 
    thông tin chi tiết từ hóa đơn Phân kim.
    """
    # Trích xuất thông tin chung (Mã PK, Tên khách hàng, SĐT, Địa chỉ)
    pk_match = re.search(r'DỊCH VỤ PHÂN KIM - TRAO ĐỔI DẺ\((PK\d+)\)', text)
    customer_match = re.search(r'Tên khách hàng:\s*([^\n]+)', text)
    phone_match = re.search(r'Số điện thoại:\s*(\d+)', text)
    address_match = re.search(r'Địa chỉ:\s*(.+?),', text) # Lấy đến dấu phẩy đầu tiên

    
    # Lấy thông tin tổng hợp (trang cuối)
    total_tl_match = re.search(r'Tổng TL nhận khách:(\d+\.\d+)\s*chỉ', text)
    total_quy_match = re.search(r'Quy 10: (\d+\.\d+)\s*chỉ', text)
    
    pk_code = pk_match.group(1) if pk_match else "N/A"
    customer_name = customer_match.group(1).strip() if customer_match else "N/A"
    phone_number = phone_match.group(1).strip() if phone_match else "N/A"
    address = address_match.group(1).strip() if address_match else "N/A"
    total_tl_receive = total_tl_match.group(1) if total_tl_match else "N/A"
    total_quy_10 = total_quy_match.group(1) if total_quy_match else "N/A"

    # Regex để tìm và nhóm toàn bộ thông tin của mỗi "Dẻ số X"
    # Mẫu tìm kiếm bắt đầu bằng "Dẻ số" và kết thúc trước "Dẻ số" tiếp theo hoặc hết chuỗi
    # Sử dụng re.DOTALL để khớp với ký tự xuống dòng
    # Thay thế '--- Hết Trang ---' bằng regex linh hoạt hơn cho các trang
    pattern = re.compile(r'(Dẻ số\s*\d.*?)(?=Dẻ số\s*\d|DỊCH VỤ PHÂN KIM|$)', re.DOTALL)
    
    data_records = []
    
    for match in pattern.finditer(text):
        dinh_danh_text = match.group(0)
        
        record = {
            "Mã PK": pk_code,
            "Khách hàng": customer_name,
            "SĐT": phone_number,
            "Địa chỉ": address,
            "Tổng TL nhận khách": total_tl_receive,
            "Tổng Quy 10": total_quy_10
        }

        # Trích xuất các trường dữ liệu chi tiết bằng Regex trong khối văn bản nhỏ hơn
        try:
            # Dẻ số
            record["Dẻ số"] = re.search(r'Dẻ số\s*(\d+)', dinh_danh_text).group(1)
            
            # 1. Vàng khách đưa (chỉ) và Tuổi vàng (%)
            vang_dua_match = re.search(r'Vàng khách đưa:\s*(\d+\.\d+)\s*chỉ.*?Tuổi vàng:\s*(\d+\.\d+)%', dinh_danh_text, re.DOTALL)
            if vang_dua_match:
                record["Vàng khách đưa (chỉ)"] = vang_dua_match.group(1)
                record["Tuổi vàng (%)"] = vang_dua_match.group(2)
            
            # 2. Phổ lần 1 và lần 2
            phoi_match = re.search(r'Phổ:\s*(\d+\.\d+)\s*%\s*,\s*(\d+\.\d+)\s*%', dinh_danh_text)
            if phoi_match:
                record["Phổ Lần 1 (%)"] = phoi_match.group(1)
                record["Phổ Lần 2 (%)"] = phoi_match.group(2)
            else:
                record["Phổ Lần 1 (%)"] = "N/A"
                record["Phổ Lần 2 (%)"] = "N/A"
            
            # 3. Thông tin phân kim(0.30) - Lấy giá trị số (ví dụ: 41.31)
            # Dùng regex linh hoạt hơn: "Thông tin phân kim(0.30) [số thập phân]"
            tt_phan_kim_match = re.search(r'Thông tin de phân kim\(0\.30\)\s*(\d+\.\d+)', dinh_danh_text, re.DOTALL)
            record["Thông tin PK (0.30)"] = tt_phan_kim_match.group(1) if tt_phan_kim_match else "N/A"

            # 4. Lai PK và Quy 10 (chỉ)
            # TL Tính (đã sửa để linh hoạt hơn)
            lai_quy_match = re.search(r'Lai PK:\s*(\d+\.\d+).*?Quy 10:\s*(\d+\.\d+)chỉ', dinh_danh_text, re.DOTALL)
            if lai_quy_match:
                record["Lai PK"] = lai_quy_match.group(1)
                record["Quy 10 (chỉ)"] = lai_quy_match.group(2)

            # 5. TL Tính và Trả vàng (cực kỳ linh hoạt)
            # Mẫu: TL Tính: <val1> chỉ (bất cứ thứ gì) <val2> chỉ.
            tl_trả_vàng_match = re.search(r'TL Tính:\s*(\d+\.\d+)\s*chỉ.*?(\d+\.\d+)\s*chỉ', dinh_danh_text, re.DOTALL)
            if tl_trả_vàng_match:
                record["TL Tính (chỉ)"] = tl_trả_vàng_match.group(1)
                record["Trả vàng (chỉ)"] = tl_trả_vàng_match.group(2)
            else:
                raise AttributeError("TL Tính or Trả vàng values not found in the expected format.")

            # 6. Quy 9999
            quy9999_match = re.search(r'Quy 9999\s*(\d+\.\d+)', dinh_danh_text, re.DOTALL)
            record["Quy 9999"] = quy9999_match.group(1) if quy9999_match else "N/A"

            # 7. TT Tiền*95
            tt_tien_match = re.search(r'TT Tiền\*95\s*(\d+\.\d+)\s*x\s*(\d+)', dinh_danh_text, re.DOTALL)
            if tt_tien_match:
                # Trích xuất cả 2 giá trị: 0.00 và 0
                record["TT Tiền*95 - L1"] = tt_tien_match.group(1)
                record["TT Tiền*95 - L2"] = tt_tien_match.group(2)
            else:
                record["TT Tiền*95 - L1"] = "N/A"
                record["TT Tiền*95 - L2"] = "N/A"
                
            # 8. Cân lại: 0.00 chỉ
            can_lai_match = re.search(r'Cân lại:\s*(\d+\.\d+)\s*chỉ', dinh_danh_text, re.DOTALL)
            record["Cân lại (chỉ)"] = can_lai_match.group(1) if can_lai_match else "N/A"


        except AttributeError as e:
            # Thêm thông tin lỗi cụ thể hơn
            print(f"Cảnh báo: Không tìm thấy đủ trường dữ liệu cho Dẻ số {record.get('Dẻ số', 'N/A')} - Lỗi: {e}")
            continue

        data_records.append(record)

    return data_records

def export_to_excel(data_list, output_file):
    """
    Chuyển List of Dictionaries sang DataFrame và xuất ra file Excel.
    """
    try:
        df = pd.DataFrame(data_list)
        # Sắp xếp lại thứ tự cột cho dễ đọc, bao gồm các cột mới
        columns_order = [
            "Mã PK", 
            "Khách hàng", 
            "SĐT",
            "Địa chỉ",
            "Dẻ số", 
            "Vàng khách đưa (chỉ)", 
            "Tuổi vàng (%)", 
            "Thông tin PK (0.30)", # Cột mới
            "Phổ Lần 1 (%)", 
            "Phổ Lần 2 (%)", 
            "Quy 9999", # Cột mới
            "Lai PK", 
            "TL Tính (chỉ)", 
            "Trả vàng (chỉ)", 
            "Quy 10 (chỉ)", 
            "Cân lại (chỉ)", # Cột mới
            "TT Tiền*95 - L1", # Cột mới
            "TT Tiền*95 - L2", # Cột mới
            "Tổng TL nhận khách", 
            "Tổng Quy 10"
        ]
        df = df[columns_order]
        
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
# Đã cập nhật sang đường dẫn tuyệt đối dựa trên ngữ cảnh của bạn.
pdf_file_path = r'D:\ThanhVu\kpht\GiaiPhapVang\read_pdf\file\input\de.pdf' 

# LƯU Ý: Nếu bạn chạy trên máy cá nhân, hãy dùng đường dẫn tuyệt đối (raw string)
# Ví dụ: pdf_file_path = r'D:\ThanhVu\kpht\GiaiPhapVang\read_pdf\file\input\de.pdf'

read_pdf_file_pdfplumber(pdf_file_path)
