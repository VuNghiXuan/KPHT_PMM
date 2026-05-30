\# QUY TRÌNH NHẬP HÀNG - VẬN HÀNH TIỆM VÀNG



\## 1. Cấu trúc Phân cấp (Hierarchy)

Quy trình được quản lý theo mô hình cây:

\- \*\*Cha (Toa hàng):\*\* Đại diện cho một lô hàng tổng thể nhập về.

\- \*\*Con (Lô hàng):\*\* Nhóm sản phẩm (ví dụ: Trang sức, Nhẫn trơn, Hàng Tân trang).

\- \*\*Cháu (Phiếu nhập hàng):\*\* Các chứng từ chi tiết cho từng phần hàng.



\## 2. Quy tắc Nghiệp vụ Đặc thù

\- \*\*Hàng Tân trang:\*\* Không yêu cầu chỉ định NCC (do gom từ nhiều nguồn).

\- \*\*Công gốc:\*\* Nhập chi tiết theo từng sản phẩm theo từng Toa hàng NCC.

\- \*\*Công vốn \& Công bán:\*\* Áp dụng công thức dựa trên quy định của NCC.

\- \*\*Tính Giá vốn sản phẩm:\*\* `Giá vốn SP = (Trọng lượng vàng \* Đơn giá vốn) + Công vốn + Tiền hột`

\- \*\*Hàng hư/lỗi:\*\* Được điều chuyển tự động từ quầy quản lý về trạng thái \*\*"Vàng nguyên liệu"\*\*.



\## 3. Trạng thái Quy trình (Workflow States)

Hệ thống sẽ kiểm tra tự động trạng thái dựa trên số lượng các phần tử con (Toa -> Lô -> Phiếu):



| Trạng thái | Điều kiện kích hoạt |

| :--- | :--- |

| \*\*Đang nhập hàng\*\* | Có ít nhất 1 Phiếu nhập hàng được khởi tạo. |

| \*\*Đã nhập hàng\*\* | Tất cả các Phiếu nhập hàng thuộc Toa hàng đã được duyệt. |

| \*\*Hoàn tất\*\* | Không còn phiếu nhập hàng chờ duyệt VÀ trạng thái đã chuyển sang "Đã nhập hàng". |



\## 4. Quản lý "Phiếu nhập hàng"

Dữ liệu được bóc tách và lưu trữ tại các Ô (Cell) tương ứng với cấu hình `Grid Kho`:

\- \*\*Cấu hình Grid:\*\* Phân loại theo Tình trạng hàng (Mới, Tân trang, Hư lỗi).

\- \*\*Trường thông tin cần có:\*\*

&#x20; - `Số phiếu nhập` | `Ngày nhập`

&#x20; - `Loại vàng` | `Hàm lượng hiển thị`

&#x20; - `Đơn giá vốn` | `Tên NCC`

&#x20; - `Chi phí phân bổ` | `Tên sản phẩm` (Trọng lượng tổng/tịnh, Mã SP, Số lượng)



\## 5. Quy trình duyệt và tạo Toa hàng

1\. \*\*Phòng tạo Toa (NT):\*\* Khởi tạo Toa hàng dựa trên thực tế.

2\. \*\*Phiếu tạo Toa:\*\* Tạo các Phiếu nhập hàng chi tiết tương ứng.

3\. \*\*Phê duyệt:\*\*

&#x20;  - Kiểm tra Toa hàng -> Lô hàng (A, B, C...).

&#x20;  - Kiểm tra Phiếu nhập (1, 2, 3...).

&#x20;  - Trạng thái chỉ được đóng "Đã duyệt" khi tất cả các nhánh con hoàn tất kiểm tra.



\## 6. Logic kiểm tra (System Validation)

\- Mỗi giai đoạn phải thực hiện `Check`:

&#x20; - `Toa hàng` có bao nhiêu `Lô hàng`?

&#x20; - `Lô hàng` có bao nhiêu `Phiếu nhập`?

\- Hệ thống không cho phép chuyển trạng thái "Đã nhập" nếu tổng trọng lượng/số lượng sản phẩm giữa các cấp bị lệch.

