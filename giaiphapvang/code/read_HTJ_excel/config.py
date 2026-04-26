import os

class Config:
    # Database
    DB_URL = "sqlite:///storage/htj_data.db"
    STORAGE_DIR = "storage"
    RAW_EXCEL_DIR = os.path.join(STORAGE_DIR, "raw_excel")
    JSON_BACKUP_PATH = os.path.join(STORAGE_DIR, "knowledge_backup.json")
    JSON_PENDING_PATH = os.path.join(STORAGE_DIR, "pending_knowledge.json")
    JSON_AI_PAYLOAD_PATH = os.path.join(STORAGE_DIR, "ai_payload_batch.json")
    
    
    # AI & Vector
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    COSINE_THRESHOLD_NEW = 0.3
    COSINE_THRESHOLD_KNOWN = 0.85
    
    # Tạo thư mục nếu chưa có
    @classmethod
    def init_directories(cls):
        os.makedirs(cls.STORAGE_DIR, exist_ok=True)
        os.makedirs(cls.RAW_EXCEL_DIR, exist_ok=True)

    # Định nghĩa nghiệp vụ
    TASK = ["VÀNG", "KẾ TOÁN", "KHO", "HỆ THỐNG", "BỎ QUA", 'MUA BÁN/ĐỔI', 'NHÀ CUNG CẤP (NCC)']
    
    # Prompt tùy biến theo từng loại file/nghiệp vụ
    TASK_PROMPTS = {
        "VÀNG": "Mày là chuyên gia định giá vàng. Hãy giải thích các thuật ngữ về tuổi vàng, loại vàng (999, 18k...), quy tuổi chuẩn nghiệp vụ tiệm vàng HTJ.",
        "KẾ TOÁN": "Mày là kế toán trưởng. Giải thích các nhãn này theo hướng hạch toán, thu chi, công nợ và thuế (Thông tư 22/99).",
        "KHO": "Mày là quản lý kho nữ trang. Giải thích theo hướng kiểm kê, mã tem, trọng lượng và bao bì.",
        "MUA BÁN/ĐỔI": "Mày là nhân viên bán hàng. Giải thích các nhãn theo hướng giao dịch với khách, đổi cũ lấy mới, bù lỗ vàng.",
        "NHÀ CUNG CẤP (NCC)": "Mày là bộ phận thu mua. Giải thích theo hướng đối chiếu với chành, NCC (APJ, Kim Tuấn Quang...)."
    }

    # Danh sách không cần định nghĩa:
    # Danh sách các nhãn Excel không mang giá trị nghiệp vụ (Blacklist)
    EXCEL_IGNORE_LABELS = [
        # Hệ thống & Giao diện
        "stt", "số tt", "số thứ tự", "module", "nhóm chức năng", "chức năng", 
        "icon", "hình ảnh", "image", ".png", ".jpg", ".svg", ".jpeg",
        
        # Nhãn chung chung
        "ghi chú", "note", "diễn giải", "tên", "ngày", "giờ", "trạng thái", "status",
        
        # Dữ liệu rác/Trống
        "unknown", "n/a", "none", "null", "-", "true", "false", "tên cột", "cột"
    ]

    DEFAULT_DEFINITIONS = {
        "stt": "Số thứ tự bản ghi trong danh sách.",
        "ghi chú": "Thông tin bổ sung hoặc lưu ý đặc biệt cho dòng dữ liệu này.",
        "tên": "Tên gọi hoặc nhãn định danh của đối tượng.",
        "ngày": "Ngày ghi nhận hoặc phát sinh giao dịch/dữ liệu.",
        "trạng thái": "Tình trạng hiện tại của bản ghi (ví dụ: Hoàn thành, Đang chờ).",
        "icon": "Biểu tượng hiển thị đại diện trên giao diện người dùng."
    }
    
Config.init_directories()