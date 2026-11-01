# 🏛️ Triết lý Cốt lõi & Kiến trúc Nền tảng (Core Philosophy)

## 1. Tư duy "Harness Engineering" ⚙️
* **AI là công cụ, Kiến trúc là khung xương:** AI đóng vai trò tăng tốc độ phát triển và tối ưu hóa mã nguồn, nhưng toàn bộ hệ thống phải được xây dựng dựa trên nền tảng kiến trúc vững chắc, tuân thủ các chuẩn mực mã nguồn mở (GitHub Standard).
* **Giảm thiểu Nợ kỹ thuật (*Technical Debt*):** Hạn chế tối đa việc tự viết các giải pháp tùy chỉnh (*custom-build*) cho những bài toán đã có thư viện chuẩn giải quyết tốt, nhằm đảm bảo khả năng bảo trì và mở rộng dài hạn.

## 2. Nguyên tắc Cô lập Dữ liệu Nhóm (Group-Centric) 🔒
* **Cô lập tuyệt đối theo `group_id`:** Mọi thao tác truy vấn dữ liệu, lưu trữ VectorDB, tạo Embedding, và caching trên Redis bắt buộc phải được lọc cứng theo `group_id` của đoạn chat/nhóm.
* **Loại bỏ các mô hình cũ:** Tuyệt đối không sử dụng các khái niệm cũ như `CompanyScoped` hay `CompanyMiddleware` để giữ cho kiến trúc Modular Monolith hoàn toàn tập trung vào thực thể `ChatGroup`.

## 3. Kiến trúc Modular Monolith 🧩
Hệ thống được phân tách thành các module độc lập rõ ràng về mặt ranh giới logic:
* 🛡️ `apps.core`: Quản lý xác thực (Auth), hồ sơ người dùng (Profile) và Context Processors.
* 💬 `apps.group_chat`: Quản lý hội thoại, thành viên, tài liệu, vòng đời tri thức và cơ chế phản hồi (Feedback).
* 🧠 `apps.ai_assistant`: Core AI xử lý RAG, Router, Vector Store, AI_Factory và AI_Engine.
* 💳 `apps.subscriptions`: Quản lý gói cước và giới hạn hạn mức (*quota*) theo nhóm.
* 📊 `apps.arch_manager`: Lưu trữ sơ đồ kỹ thuật và nội soi hệ thống (*SystemBlueprint*).