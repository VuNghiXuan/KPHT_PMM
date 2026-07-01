\# 📑 TÀI LIỆU KIẾN THỨC NGHIỆP VỤ: LOGIC GIAO DỊCH VÀ QUY ĐỔI CÔNG NỢ NHÀ CUNG CẤP (NCC)



\## 1. TỪ ĐIỂN THUẬT NGỮ CHUẨN HÓA (KNOWLEDGE BASE)

Hệ thống ChatBot cần phân biệt rõ bản chất các loại "Tuổi vàng" trong giao dịch với Nhà cung cấp (NCC) để tránh nhầm lẫn với cấu trúc giá bán lẻ tại cửa hàng:



\* \*\*Tuổi Vàng (Hàm lượng vàng):\*\* Trong giao dịch với NCC, tuổi vàng được ngầm hiểu chính là hàm lượng/tỷ lệ vàng tinh khiết của sản phẩm.

\* \*\*Tuổi Thu (Tuổi mua vào của NCC):\*\* Là tỷ lệ tuổi vàng mà NCC sẽ áp dụng khi thu mua lại hàng hóa từ tiệm. Tuổi thu này \*không cố định\* mà phụ thuộc vào từng NCC và từng \*\*Loại hàng NCC\*\* (biến thể sản phẩm).

&#x20;   \* \*Ví dụ (NCC Tuấn Kiệt - Loại vàng 610):\* \* Hàng Bọng (Tay) NCC $\\rightarrow$ Tuổi thu là `61.0` (61%)

&#x20;       \* Hàng Simen 1.0 NCC $\\rightarrow$ Tuổi thu là `61.50` (61.5%)

\* \*\*Tuổi Bán (Tuổi bán ra của NCC):\*\* Là tỷ lệ tuổi vàng mà NCC áp cho tiệm khi tiệm mua hàng của họ. Quy luật: \*\*Tuổi Bán $\\ge$ Tuổi Thu\*\*. Chênh lệch giữa Tuổi Bán và Tuổi Thu chính là phần lợi nhuận bản thương mại và bù đắp chi phí hao hụt trong chế tác của NCC.

&#x20;   \* \*Ví dụ (NCC Tuấn Kiệt - Loại vàng 610):\* \* Hàng Bọng (Tay) NCC $\\rightarrow$ Tiệm phải mua với Tuổi bán là `63.0` (63%)

&#x20;       \* Hàng Simen 1.0 NCC $\\rightarrow$ Tiệm phải mua với Tuổi bán là `62.5` (62.5%)

\* \*\*Tuổi Tính Công Nợ (Tuổi Ghi Nhận Công Nợ):\*\* Là giá trị tuổi vàng chuẩn do NCC quy định nhằm mục đích quy đổi trọng lượng các loại vàng khác nhau về cùng một hệ quy chiếu, giúp hai bên dễ dàng đối chiếu thanh toán chênh lệch.

\* \*\*Loại Vàng Ghi Nhận Công Nợ:\*\* Là loại vàng chuẩn được chọn làm mốc thanh toán công nợ sau khi quy đổi (Thường dùng loại vàng chuẩn như Vàng tinh khiết 100% hay còn gọi là Vàng 10 theo tiếng lóng nghiệp vụ toa hàng, hoặc Vàng 99.99).



\---



\## 2. MA TRẬN PHÂN LOẠI VÀ CHÊNH LỆCH TUỔI (BÁN VÀ THU)

\*Bảng này giúp ChatBot hiểu logic biên lợi nhuận ẩn của NCC trên từng loại mặt hàng khi xử lý hóa đơn:\*



| Nhà Cung Cấp | Loại Vàng | Loại Hàng NCC | Tuổi Bán (Tiệm Mua) | Tuổi Thu (Tiệm Bán Lại) | Chênh Lệch Lợi Nhuận |

| :--- | :--- | :--- | :--- | :--- | :--- |

| \*\*NCC Tuấn Kiệt\*\* | 610 | Hàng Bọng (Tay) | \*\*63.0\*\* | \*\*61.0\*\* | + 2.0 (Tuổi) |

| \*\*NCC Tuấn Kiệt\*\* | 610 | Hàng Simen 1.0 | \*\*62.5\*\* | \*\*61.5\*\* | + 1.0 (Tuổi) |



\---



\## 3. HỆ THỐNG CÔNG THỨC TOÁN HỌC TRÊN TOA HÀNG NCC

ChatBot khi lập trình hoặc đọc hiểu file Excel/Hóa đơn Toa hàng phải áp dụng chính xác 4 công thức toán học sau:



\### 3.1. Công thức tính Trọng lượng vàng thực tế (TLV)

Trọng lượng vàng thuần ký sau khi đã trừ trọng lượng hột/đá gắn trên sản phẩm.

$$\\text{TLV} = \\text{Tổng TL} - \\text{TL Hột}$$



\### 3.2. Công thức Quy đổi Tuổi vàng ghi nhận công nợ

Tỷ lệ dùng để nhân hệ số quy đổi trọng lượng về loại vàng công nợ chuẩn.

$$\\text{Tỷ lệ Quy Đổi} = \\frac{\\text{Tuổi Bán}}{\\text{Tuổi Tính Công Nợ}}$$



\### 3.3. Công thức tính Trọng lượng vàng quy đổi (TLV Quy)

Trọng lượng vàng thực tế sau khi quy về loại vàng ghi nhận công nợ chuẩn (Cột `TLV Quy` trong bảng dữ liệu).

$$\\text{TLV Quy} = \\text{TLV} \\times \\left( \\frac{\\text{Tuổi Bán}}{\\text{Tuổi Tính Công Nợ}} \\right)$$



\### 3.4. Công thức tính Giá trị vàng thành tiền (Vàng tính thành tiền)

Áp dụng cho dòng sản phẩm thanh toán bằng tiền mặt dựa trên giá vàng mốc công nợ (Giá vàng 10 - đại diện cho vàng tinh khiết 100%).

$$\\text{Vàng tính thành tiền} = \\text{Giá vàng 10} \\times \\left( \\frac{\\text{Tuổi Bán}}{100} \\right)$$



\---



\## 4. HƯỚNG DẪN ĐỌC HIỂU DỮ LIỆU THỰC TẾ (DÀNH CHO LLM ENGINE)

\*Dựa trên hình ảnh bảng tính mẫu, cấu trúc dữ liệu Toa hàng được chia làm hai phần chính:\*



\### Lớp dữ liệu 1: Chi tiết các dòng Toa hàng (Dòng 1 đến 10)

\* \*\*Dòng 1 (Vàng 9999):\*\* `Tuổi bán/Tuổi tính công nợ` = `99.99/99.99` $\\rightarrow$ Tỷ lệ quy đổi = 1. `TLV Quy` giữ nguyên = `12.5540`.

\* \*\*Dòng 2 \& 3 (Vàng 980):\*\* `Tuổi bán/Tuổi tính công nợ` = `98.50/98.50` $\\rightarrow$ Tỷ lệ quy đổi = 1. `TLV Quy` giữ nguyên.

\* \*\*Dòng 5 (Vàng 610 - Đổi ngang):\*\* `Tuổi bán/Tuổi tính công nợ` = `63.00/62.20`. 

&#x20;   \* \*Tính toán:\* $\\text{TLV Quy} = 19.5360 \\times (63.00 / 62.20) = \\mathbf{19.7873}$ (Khớp hoàn toàn với ô E5 trên Excel).

\* \*\*Dòng 9 (Vàng 416 - Tất cả):\*\* `Tuổi bán/Tuổi tính công nợ` = `42.6/100`. Loại vàng ghi nhận công nợ quy về `99.99`.

&#x20;   \* \*Tính toán:\* $\\text{TLV Quy} = 195.1440 \\text{ (Tổng TL)} - 4.2050 \\text{ (TL hột)} = 190.9390 \\text{ (TLV)}$.

&#x20;   \* $\\text{TLV Quy} = 190.9390 \\times (42.6 / 100) = \\mathbf{81.3400}$ (Khớp hoàn toàn với ô E9 trên Excel).

\* \*\*Dòng 10 (Vàng 750):\*\* Không quy đổi trọng lượng (`TLV Quy` = `25.3095`), cột `vàng tính thành tiền` ghi nhận số tiền trực tiếp: $\\mathbf{398,100,497 \\text{ VND}}$.



\### Lớp dữ liệu 2: Bảng giá đối chiếu chân trang

Bảng giá này đóng vai trò cung cấp tham số `Giá vàng 10` hiện tại để tính toán cột thành tiền.

\* Mốc giá cơ sở `Giá vàng 10` = \*\*16,423,000 VND\*\*.

\* \*\*Tỷ giá vàng 9999\*\* = $16,423,000 \\times (99.99 / 100) = \\mathbf{16,421,358 \\text{ VND}}$.

\* \*\*Tỷ giá vàng 610\*\* = $16,423,000 \\times (63 / 100) = \\mathbf{10,346,490 \\text{ VND}}$.

