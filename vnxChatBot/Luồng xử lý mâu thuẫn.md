sequenceDiagram
    autonumber
    actor Admin as Quản trị viên nhóm
    participant View as Lifecycle/Conflict Views
    participant Service as Conflict/Knowledge Service
    participant DB as Database (KnowledgeChapter)
    participant Vector as Vector Store

    Admin->>View: Gửi yêu cầu duyệt/sửa/giải quyết mâu thuẫn (Update/Merge/Ignore)
    View->>Service: Gọi hàm xử lý nghiệp vụ theo group_id
    Service->>DB: Cập nhật trạng thái (Pending -> Approved) & Lưu nội dung chỉnh sửa
    Note over DB,Vector: Dữ liệu chuyển sang Approved kích hoạt Signal
    DB-->>Vector: Tự động đồng bộ Embedding vào Vector Store
    Service-->>View: Trả về kết quả thành công
    View-->>Admin: Hiển thị thông báo hoàn tất & cập nhật giao diện