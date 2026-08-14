# 🧪 Quy chuẩn Phát triển & Kiểm thử (Development & Testing Protocols)

## 1. Quy chuẩn Viết Mã (Coding Standards) 💻
* **Modular Monolith Integrity:** Mọi đoạn code mới phải tuân thủ nghiêm ngặt ranh giới giữa các module (`apps.core`, `apps.group_chat`, `apps.ai_assistant`, v.v.). Tuyệt đối không tạo ra các đường tắt (*shortcuts*) vi phạm tính cô lập của `group_id`.
* **Atomic Updates:** Khi cung cấp mã nguồn, luôn xuất ra các khối code hoàn chỉnh, kèm theo chú thích giải thích rõ ràng và phương án dự phòng (*Rollback plan*).
* **Clean Code & Token Efficiency:** Loại bỏ hoàn toàn các đoạn mã rác, giữ cho mã nguồn tinh gọn và tối ưu hóa chi phí ngữ cảnh khi xử lý qua AI.

## 2. Quy trình Kiểm thử Bắt buộc (Mandatory Test Protocol) 🔬
* **Test-Driven Mindset:** Mọi tính năng hoặc module mới bắt buộc phải đi kèm Unit Test được đặt tại thư mục `apps/<module>/tests/`.
* **Database Preservation:** Sử dụng cờ `--keepdb` khi chạy các lệnh kiểm thử của Django để tối ưu hóa thời gian thực thi:
  ```bash
  python manage.py test apps.ai_assistant --keepdb