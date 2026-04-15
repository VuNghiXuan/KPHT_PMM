import PyPDF2
import os

def read_pdf_file(file_path):
    """
    Trích xuất toàn bộ văn bản từ một file PDF.

    Args:
        file_path (str): Đường dẫn đến file PDF cần đọc.
    """
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại đường dẫn: {file_path}")
        return

    try:
        # Mở file PDF ở chế độ nhị phân ('rb')
        with open(file_path, 'rb') as file:
            # Tạo đối tượng PDF Reader
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Khởi tạo chuỗi để lưu trữ toàn bộ văn bản
            text = ""
            
            # Lặp qua từng trang trong tài liệu
            for page_num in range(len(pdf_reader.pages)):
                # Trích xuất trang
                page = pdf_reader.pages[page_num]
                # Trích xuất văn bản và thêm vào chuỗi
                text += page.extract_text()
                
        # In kết quả trích xuất
        print(f"--- Đã trích xuất văn bản từ {len(pdf_reader.pages)} trang ---")
        print(text)
        
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình đọc file PDF: {e}")

# --- CÁCH SỬ DỤNG ---
# Thay thế 'your_document.pdf' bằng đường dẫn file PDF thực tế của bạn
pdf_file_path = r'D:\ThanhVu\kpht\GiaiPhapVang\read_pdf\file\input\de.pdf' 
# Nếu file của bạn nằm cùng thư mục với file code Python, bạn chỉ cần ghi tên file.

read_pdf_file(pdf_file_path)

# pip install PyPDF2