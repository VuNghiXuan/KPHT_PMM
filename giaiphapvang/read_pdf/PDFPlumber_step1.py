import pdfplumber
import os

def read_pdf_file_pdfplumber(file_path):
    """
    Trích xuất toàn bộ văn bản từ một file PDF bằng thư viện pdfplumber.

    Args:
        file_path (str): Đường dẫn đến file PDF cần đọc.
    """
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại đường dẫn: {file_path}")
        return

    try:
        # Mở file PDF bằng pdfplumber.open()
        with pdfplumber.open(file_path) as pdf:
            
            # Khởi tạo chuỗi để lưu trữ toàn bộ văn bản
            text = ""
            
            # Lặp qua từng trang trong tài liệu
            for page in pdf.pages:
                # Trích xuất văn bản từ trang
                page_text = page.extract_text()
                
                # Thêm văn bản của trang vào chuỗi tổng hợp
                if page_text:
                    text += page_text + "\n--- Hết Trang ---\n"
                
        # In kết quả trích xuất
        print(f"--- Đã trích xuất văn bản từ {len(pdf.pages)} trang ---")
        print(text)
        
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình đọc file PDF: {e}")

# --- CÁCH SỬ DỤNG ---
# Thay thế 'your_document.pdf' bằng đường dẫn file PDF thực tế của bạn
# Ví dụ, nếu bạn dùng đường dẫn thử nghiệm cho file "de.pdf"
pdf_file_path = r'D:\ThanhVu\kpht\GiaiPhapVang\read_pdf\file\input\de.pdf' 
# HOẶC: pdf_file_path = r'D:\ThanhVu\kpht\GiaiPhapVang\read_pdf\file\input\de.pdf' 

read_pdf_file_pdfplumber(pdf_file_path)