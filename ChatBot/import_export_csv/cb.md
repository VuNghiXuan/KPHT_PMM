# CHIẾN LƯỢC PHÁT TRIỂN HỆ THỐNG TRI THỨC Ứng Dụng Vàng (CHATBOT_HTJ)

Hệ thống này được định vị là một **"Trợ lý Nghiệp vụ số"** có khả năng hiểu sâu, hướng dẫn quy trình và tự học từ dữ liệu đặc thù của ngành vàng và xây dựng tại Kim Phát Hiệp Thành (HTJ/Ứng Dụng Vàng).

---

## 1. Kiến trúc phân tầng hệ thống (Core Apps)

Để đảm bảo khả năng mở rộng và xử lý dữ liệu lớn, hệ thống được chia thành 4 module độc lập với nhiệm vụ rõ ràng:

### 🛠️ app_miner (Lớp Bóc tách dữ liệu)
*   **Nhiệm vụ:** Hoạt động như "tai mắt" của hệ thống. Chuyên trách thu nhận dữ liệu từ các nguồn phi cấu trúc.
*   **Chức năng chính:** 
    *   Xử lý file `Excel` nghiệp vụ (sử dụng Openpyxl/Pandas).
    *   Trích xuất văn bản từ `PDF` kỹ thuật.
    *   Sử dụng `OCR` (Tesseract/OpenCV) để đọc dữ liệu từ hình ảnh (bảng giá vàng, hóa đơn).
*   **Đầu ra:** Dữ liệu có cấu trúc, có tọa độ (coordinates) và định dạng chuẩn để máy tính xử lý.

### 🧠 app_knowledge (Lớp Tri thức - GraphRAG)
*   **Nhiệm vụ:** "Não bộ" của hệ thống, lưu trữ mối quan hệ logic giữa các con số và văn bản nghiệp vụ.
*   **Công nghệ:** Sử dụng **Neo4j** làm cơ sở dữ liệu đồ thị để ánh xạ các mối liên kết phức tạp (ví dụ: *Loại vàng -> Nhà cung cấp -> Công thức tính phí*).
*   **Đặc điểm:** Thay vì chỉ lưu trữ dạng bảng (SQL) đơn thuần, GraphRAG cho phép AI truy xuất tri thức dựa trên ngữ cảnh và quan hệ thực tế.

### 🎓 app_coach (Lớp Huấn luyện & Học tăng cường)
*   **Nhiệm vụ:** Cầu nối tương tác giữa AI và Quản trị viên (anh Vũ).
*   **Chức năng chính:** 
    *   Quản lý trạng thái "mông lung" khi AI gặp khái niệm mới.
    *   Cung cấp giao diện duyệt lỗi (Correction Interface) để Admin hiệu chỉnh phản hồi của AI.
    *   Lưu trữ nhật ký sửa lỗi để AI thực hiện học tăng cường (Fine-tuning tri thức).

### 🤖 app_chat_agent (Lớp Điều phối & Phản hồi)
*   **Nhiệm vụ:** Tiếp nhận yêu cầu, phân tích ý định (Intent) và trả lời người dùng.
*   **Chức năng chính:** 
    *   Điều phối luồng công việc giữa các App khác.
    *   Truy xuất dữ liệu từ `app_knowledge` để đưa ra câu trả lời có tính chuyên gia và chính xác cao.

---

## 2. Thiết kế Cơ sở dữ liệu & Mô hình hóa Tri thức (Schema)

### A. Nhóm Quản lý Tài liệu (Sử dụng SQL)
| Model | Trường dữ liệu (Fields) | Ý nghĩa nghiệp vụ |
| :--- | :--- | :--- |
| **ExcelProject** | `name`, `created_at` | Quản lý dự án dữ liệu theo giai đoạn. |
| **ExcelSheet** | `project`, `sheet_name` | Định danh nghiệp vụ cụ thể (Ví dụ: "Phân loại trả NCC"). |
| **ExcelTableRegion**| `coordinates`, `region_type` | Phân vùng Header, Data, và Popup để AI định hướng tọa độ bóc tách. |

### B. Nhóm Định nghĩa Nghiệp vụ (Sử dụng Neo4j)
Giúp AI hiểu "luật chơi" của HTJ thay vì chỉ đọc văn bản thô.

*   **Model BusinessTerm (Từ điển Tri thức):**
    *   **Trường:** `term` (TLV, Tỷ giá...), `definition` (Giải nghĩa), `formula_logic` (Logic tính toán).
    *   **Công dụng:** Giải mã thuật ngữ chuyên ngành. Gặp từ mới, AI tự động yêu cầu huấn luyện qua `app_coach`.
*   **Model BusinessProcess (Luồng Quy trình):**
    *   **Trường:** `process_name`, `steps` (JSON các bước), `required_fields` (Ô bắt buộc).
    *   **Công dụng:** Hướng dẫn người dùng nhập liệu đúng quy trình (Ví dụ: *"Bước này cần nhập Nhà cung cấp trước"*).

### C. Nhóm Học tăng cường & Giám sát
*   **Model CorrectionLedger:** Nhật ký lưu trữ mọi thao tác sửa lỗi của anh Vũ. Đây là tập dữ liệu quý giá để AI không lặp lại lỗi sai.
*   **Model ConflictDetector:** Tự động phát hiện mâu thuẫn dữ liệu giữa các sheet (Ví dụ: Cùng một mã vàng nhưng hai nơi ghi hai giá khác nhau).

---

## 3. Quy trình vận hành "Chuyên gia tư vấn" (Workflow)

1.  **Nhận diện (Intent Detection):** AI phân tích câu hỏi người dùng trên Neo4j để xác định nghiệp vụ tương ứng (Ví dụ: *"Đây là quy trình trả hàng Nhà cung cấp"*).
2.  **Hướng dẫn (Active Guidance):** AI chủ động nhắc nhở người dùng các ô còn trống hoặc nhập sai dựa trên `BusinessProcess`.
3.  **Xử lý Mông lung (Uncertainty Handling):** Khi xuất hiện thuật ngữ mới chưa có định nghĩa, AI ghi vào `UncertaintyLog` và đặt câu hỏi cho Admin: *"Anh Vũ ơi, thuật ngữ 'Vàng bộng 2' tính phí thế nào?"*.
4.  **Học tập vĩnh viễn:** Sau khi Admin giải đáp, tri thức mới được cập nhật vào `app_knowledge` và trở thành tài sản vĩnh viễn của hệ thống.
5.  **Kiểm tra chéo (Cross-check):** AI tự động thực hiện tính toán lại và đối chiếu kết quả giữa các sheet để phát hiện sai lệch trước khi người dùng kịp nhận ra.

---

## 4. Kế hoạch hành động (Action Plan)

1.  **Trục GraphRAG làm cốt lõi:** Mọi dữ liệu từ `app_miner` phải được ánh xạ thành các Node/Relationship trong Neo4j thay vì chỉ nằm lại ở SQL.
2.  **Cơ chế Duyệt tri thức:** Xây dựng dashboard Admin trong `app_coach` để anh Vũ dễ dàng "phê duyệt" tri thức mới hàng ngày.
3.  **Agentic RAG:** Cấp quyền cho AI tự sử dụng các công cụ tính toán để phát hiện mâu thuẫn dữ liệu tự động giữa hơn 300 sheet Excel.