import os

class Config:
    # Database
    DB_URL = "sqlite:///storage/htj_data.db"
    STORAGE_DIR = "storage"
    RAW_EXCEL_DIR = os.path.join(STORAGE_DIR, "raw_excel")
    JSON_BACKUP_PATH = os.path.join(STORAGE_DIR, "knowledge_backup.json")
    
    # AI & Vector
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    COSINE_THRESHOLD_NEW = 0.3
    COSINE_THRESHOLD_KNOWN = 0.85
    
    # Tạo thư mục nếu chưa có
    @classmethod
    def init_directories(cls):
        os.makedirs(cls.STORAGE_DIR, exist_ok=True)
        os.makedirs(cls.RAW_EXCEL_DIR, exist_ok=True)

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