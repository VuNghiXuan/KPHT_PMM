

<!-- --- CHUNK #1 --- -->

### Context: Sheet 'Sheet1'

#### nan

- I. Mục đích và Phạm vi

#### nan

- Mục đích của quy trình là phân loại chi tiết các mặt hàng vàng hư hỏng theo từng Nhà cung cấp (NCC) và Loại hàng NCC,
 tính toán chính xác Hao hụt phát sinh sau quá trình làm sạch, và cập nhật lại giá vốn để chuẩn bị cho việc trả NCC.

#### Nguyên tắc cốt lõi: Luôn đảm bảo nguyên tắc 1 Phiếu chỉ làm 1 Loại vàng để duy trì tính nhất quán về chất lượng.

- Nguyên tắc cốt lõi: Luôn đảm bảo nguyên tắc 1 Phiếu chỉ làm 1 Loại vàng để duy trì tính nhất quán về chất lượng.
- II. Logic Trình tự và Thao tác trên Hệ thống
- Quy trình được chia thành ba giai đoạn chính, được thực hiện qua các khu vực khác nhau của form "PHIẾU PHÂN LOẠI TRẢ NCC":

#### Giai đoạn 1: Chuẩn bị và Ghi nhận Gốc (Lấy dữ liệu Giao đi)

- Giai đoạn 1: Chuẩn bị và Ghi nhận Gốc (Lấy dữ liệu Giao đi)
- Khu vực/Form
- THÔNG TIN CHUNG
- POP-UP Thêm Chi tiết
- Lưu Pop-up

#### Giai đoạn 2: TAB1 (Kiểm soát Gốc) và Xử lý Thủ công

- Giai đoạn 2: TAB1 (Kiểm soát Gốc) và Xử lý Thủ công
- Khu vực/Form

#### TAB1: Thông tin Chi tiết

- TAB1: Thông tin Chi tiết
- Ngoài Phần mềm

#### Giai đoạn 3: TAB2 (Nhập liệu Kết quả & Kiểm soát Cuối)

- Giai đoạn 3: TAB2 (Nhập liệu Kết quả & Kiểm soát Cuối)
- Khu vực/Form

#### TAB2: Kết quả Phân loại

- TAB2: Kết quả Phân loại
- TAB2
- Hệ thống
- Hoàn tất
- III. Tóm tắt Cơ chế Kiểm soát (Logic Kế toán Quản trị)
- Quy trình này kiểm soát tính toàn vẹn của hàng hóa qua các điểm sau:

#### 1. Kiểm soát Loại vàng: Đảm bảo tính nhất quán (1 Phiếu = 1 Loại vàng).

- 1. Kiểm soát Loại vàng: Đảm bảo tính nhất quán (1 Phiếu = 1 Loại vàng).

#### 2. Kiểm soát Lượng vàng (TAB1 vs TAB2): Tính toán và quản lý Hao hụt bằng cách so sánh Trọng lượng Gốc (TAB1) với Trọng lượng Cuối (TAB2).

- 2. Kiểm soát Lượng vàng (TAB1 vs TAB2): Tính toán và quản lý Hao hụt bằng cách so sánh Trọng lượng Gốc (TAB1) với Trọng lượng Cuối (TAB2).

#### 3. Kiểm soát Giá vốn: Sau khi trừ hao hụt, giá trị hàng hóa được tính lại (Tính lại Tỷ giá/Thành tiền), đảm bảo kho luôn phản ánh đúng giá vốn của hàng tồn kho.

- 3. Kiểm soát Giá vốn: Sau khi trừ hao hụt, giá trị hàng hóa được tính lại (Tính lại Tỷ giá/Thành tiền), đảm bảo kho luôn phản ánh đúng giá vốn của hàng tồn kho.
- Chú ý: Form này liên kết với phiếu xuất kho