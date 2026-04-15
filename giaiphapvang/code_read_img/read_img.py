import easyocr
import cv2
import numpy as np
import os

# ------------------------------------------------------------------------------------------------
# CẤU HÌNH EASYOCR (Chạy một lần duy nhất)
# ------------------------------------------------------------------------------------------------
try:
    # Khởi tạo Reader: Chọn ngôn ngữ Tiếng Việt (vi) và Tiếng Anh (en)
    # Cần kết nối Internet lần đầu chạy để tải mô hình
    reader = easyocr.Reader(['vi', 'en'])
except Exception as e:
    print(f"LỖI: Không thể khởi tạo EasyOCR Reader. {e}")
    reader = None

def preprocess_and_extract_text_easyocr(image_path):
    """
    Tiền xử lý ảnh (OpenCV) và thực hiện OCR (EasyOCR).
    """
    if reader is None:
        return "LỖI: EasyOCR Reader không được khởi tạo thành công."
    
    # Kiểm tra đường dẫn tuyệt đối
    full_path = os.path.abspath(image_path)
    if not os.path.exists(full_path):
        return f"LỖI ĐƯỜNG DẪN: Không tìm thấy tệp ảnh tại đường dẫn: {full_path}"

    try:
        # 1. Đọc ảnh (dùng OpenCV)
        img = cv2.imread(full_path)
        
        if img is None:
            return f"LỖI ĐỌC ẢNH: OpenCV không thể đọc tệp tại {full_path}. Tệp có thể bị hỏng."

        # 2. Chuyển sang ảnh Xám (Grayscale)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 3. Làm sạch nhiễu (Gaussian Blur)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # 4. Phân ngưỡng Thích ứng (Adaptive Thresholding)
        # Kỹ thuật tốt cho tài liệu chụp có ánh sáng không đều
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        preprocessed_img = thresh 
        
        # 5. Thực hiện OCR trên ảnh đã xử lý bằng EasyOCR
        # Sử dụng paragraph=True để cố gắng duy trì trật tự theo khối
        results = reader.readtext(preprocessed_img, paragraph=True) 

        extracted_text = ""
        
        # 6. Xử lý kết quả: Nối các khối văn bản được nhận diện
        for result in results:
            text = ""
            if isinstance(result, str):
                text = result # Trường hợp paragraph=True trả về chuỗi
            elif isinstance(result, list) and len(result) >= 2 and isinstance(result[1], str):
                text = result[1] # Trường hợp [bbox, text, conf]
            
            if text:
                extracted_text += text + "\n" # Dùng \n để tách các khối

        if not extracted_text.strip():
             return "LỖI TRÍCH XUẤT: EasyOCR đã chạy nhưng không phát hiện được văn bản nào."
             
        return extracted_text.strip()
    
    except Exception as e:
        return f"Đã xảy ra lỗi trong quá trình OCR EasyOCR: {e}"

# ------------------------------------------------------------------------------------------------
# KHU VỰC THỬ NGHIỆM
# ------------------------------------------------------------------------------------------------
# Đường dẫn tệp ảnh bạn đang sử dụng
image_file = r'src\610.jpg' 

# Gọi hàm và in kết quả
extracted_data = preprocess_and_extract_text_easyocr(image_file)

print(f"--- Dữ liệu được trích xuất từ {image_file} (OpenCV + EasyOCR) ---")
print(extracted_data)