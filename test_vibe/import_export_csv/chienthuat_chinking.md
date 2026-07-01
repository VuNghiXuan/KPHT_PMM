### 🗺️ Giai đoạn 1: Chunking & Map (Chia để trị)
- Khi File > `max_token_threshold`: Hệ thống tự động băm nhỏ file thành các cụm 8,000 - 10,000 tokens.
- Phân phối các cụm này cho các API Keys khác nhau để tránh dính lỗi 429 (Too Many Requests).
- Nhiệm vụ của AI phụ: Tóm tắt lõi nghiệp vụ và lọc nhiễu.

### 📊 Giai đoạn 2: Quản trị Token (Auditing)
- Hệ thống kiểm tra bảng thống kê `AITokenLog` trước khi phát lệnh.
- Nếu tổng số token/lượt gọi còn lại trong ngày không đủ đáp ứng chuỗi luồng xử lý -> Tự động chuyển luồng (Fallback) về Local Ollama để bảo vệ hệ thống.

### 💤 Giai đoạn 3: Reduce (Tổng hợp)
- Con AI cuối cùng gom các bản tóm tắt tinh khiết để xuất ra tài liệu BA hoàn chỉnh.