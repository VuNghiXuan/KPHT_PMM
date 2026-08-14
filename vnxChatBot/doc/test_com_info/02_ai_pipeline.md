# 🧠 Tầng AI Pipeline & Vòng đời Tri thức (AI Pipeline & Knowledge Lifecycle)

## 1. Tầng Gateway & Router 🌐
* **LiteLLM Standardization:** Sử dụng LiteLLM làm lớp chuẩn hóa API duy nhất cho mọi mô hình ngôn ngữ, giúp dễ dàng chuyển đổi nhà cung cấp mà không thay đổi logic mã nguồn.
* **Circuit Breaker thông minh:** Tự động giám sát độ trễ và lỗi để điều hướng chuyển đổi linh hoạt giữa Cloud LLM (Gemini) và Local LLM (Ollama).
* **Redis Semantic Cache:** Áp dụng ngưỡng tương đồng $\ge 0.92$ trên Redis RAM để lưu trữ các ý định truy vấn trùng lặp, tối ưu hóa tốc độ phản hồi dưới 2 mili-giây và cắt giảm chi phí token.

## 2. Tầng Tiền xử lý & Trích xuất (AI Engine) 📄
* **Parsing chuẩn hóa (Docling / Marker):** Mọi tài liệu thô (Word, PDF, Excel) được bóc tách cấu trúc phân cấp (Heading, Điều, Khoản, Bảng biểu) và chuyển đổi sang định dạng Markdown/JSON trung gian.
* **AI Data Auditor (Kiểm toán viên dữ liệu):** Celery Task tự động chạy ngầm ngay sau khi upload để phân loại cấu trúc, dự đoán mục lục thông qua Context Clustering.
* **Chấm điểm tin cậy (Confidence Score):** Đánh giá độ tin cậy từ $0.0 - 1.0$. Các tài liệu có điểm thấp hoặc cấu trúc không đạt chuẩn sẽ được định hướng vào hàng chờ kiểm duyệt (*Human-in-the-loop*).

## 3. Vòng đời Tri thức & Xử lý Mâu thuẫn 🔄
* **Quy trình 4 trạng thái nghiêm ngặt:** 
  `Pending` $\rightarrow$ `Staging/Analysis` $\rightarrow$ `Approved` $\rightarrow$ `Rollback`.
* **Nguyên tắc Vàng VectorDB:** Dữ liệu ở trạng thái `pending` hoặc `staging` **cấm tuyệt đối** không được đẩy vào Vector Store. Chỉ khi chuyển sang `approved`, tín hiệu `signals.py` mới kích hoạt quá trình tạo Embedding.
* **Semantic Overlap Detection:** Trước khi lưu trữ, hệ thống chạy Cosine Similarity so sánh với kho dữ liệu trong cùng `group_id`. Nếu độ trùng lặp $\ge 0.85$, hệ thống gắn nhãn `Conflict Detected` và đề xuất 3 hành động: Ghi đè (Update) | Hợp nhất (Merge) | Bỏ qua (Ignore).
* **Cấu trúc lai (Hybrid Structuring):** Tạo ra cây mục lục gợi ý (`raw_structure_json`) cho phép quản trị viên sắp xếp lại nội dung trực quan trước khi chính thức phê duyệt.