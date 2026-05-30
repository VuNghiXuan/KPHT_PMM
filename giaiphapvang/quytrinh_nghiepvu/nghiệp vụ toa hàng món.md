📑 TÀI LIỆU KIẾN THỨC NGHIỆP VỤ: LOGIC TOA HÀNG MÓN THEO NHÀ CUNG CẤP (NCC)



1\. TỪ ĐIỂN THUẬT NGỮ CHUẨN HÓA (GLOSSARY)



Để Chatbot hỗ trợ tính toán và đối chiếu toa hàng chính xác, cần định nghĩa rõ bản chất các thực thể dữ liệu sau:



Toa hàng món: Giao dịch nhập hàng từ NCC theo đơn vị "Món" (trang sức nguyên chiếc như nhẫn, bông tai, dây chuyền) thay vì cân ký tính tuổi thông thường.



Thành tiền ban đầu: Giá trị cốt lõi của số lượng món hàng dựa trên đơn giá gốc chưa tính toán chi phí phát sinh.



Chi phí chứng từ: Chi phí thực tế phải trả để NCC xuất hóa đơn GTGT (VAT) hoặc các chứng từ pháp lý đi kèm để hợp thức hóa nguồn gốc hàng hóa đầu vào.



Chi phí phát sinh (Chi phí khác): Các chi phí vận chuyển, kiểm định, xi mạ hoặc chi phí ngoài được phân bổ trực tiếp cho toa hàng.



Chiết khấu phân bổ: Chính sách giảm giá hoặc ưu đãi đặc biệt NCC áp dụng cho cả toa hàng hoặc chương trình cụ thể, được chia nhỏ (phân bổ) đều theo tỷ lệ số món.



Đơn giá vốn (ĐG Vốn): Giá trị thực tế cuối cùng của một món hàng sau khi đã cộng gộp mọi chi phí phát sinh và trừ đi phần chiết khấu được hưởng. Đây là mốc giá cốt lõi để tiệm vàng làm căn cứ tính giá bán lẻ ra thị trường.



2\. HỆ THỐNG CÔNG THỨC TOÁN HỌC TOA HÀNG MÓN (EXCEL LOGIC)



Chatbot khi bóc tách bảng tính Excel hoặc tính toán kiểm tra chéo (Cross-check) toa hàng món của NCC bắt buộc phải áp dụng hệ thống 5 công thức chuẩn hóa sau:



2.1. Công thức tính Thành tiền ban đầu



Giá trị tiền hàng thô chưa gồm chi phí hay chiết khấu:





$$\\text{Thành tiền ban đầu} = \\text{Số món} \\times \\text{Đơn giá}$$



2.2. Công thức tính Tổng chi phí phát sinh của Toa hàng



Tổng hợp mọi chi phí để đưa món hàng về trạng thái sẵn sàng bán:





$$\\text{Chi phí} = \\text{Chi phí chứng từ} + \\text{Chi phí khác 1} + \\text{Chi phí khác 2}$$



2.3. Công thức tính Tổng tiền (Chi phí thực tế bỏ ra)



Tổng số tiền thực tế tiệm phải thanh toán cho NCC trước khi áp dụng chiết khấu:





$$\\text{Tổng tiền} = \\text{Thành tiền ban đầu} + \\text{Chi phí}$$



2.4. Công thức phân bổ Chiết khấu



Chính sách chiết khấu của NCC thường áp dụng trên tổng toa hàng, hệ thống bắt buộc phải phân bổ đều xuống từng dòng sản phẩm theo tỷ lệ số món:



Bước 1: Tính giá trị chiết khấu trung bình trên mỗi món:





$$\\text{Giá món chiết khấu} = \\frac{\\text{Tổng tiền chiết khấu của toa hàng}}{\\text{Tổng số món của toàn bộ toa hàng}}$$



Bước 2: Tính Chiết khấu phân bổ của từng dòng sản phẩm:





$$\\text{Chiết khấu phân bổ} = \\text{Giá món chiết khấu} \\times \\text{Số món}$$



2.5. Công thức tính Đơn giá vốn thực tế (ĐG Vốn)



Đây là giá vốn sau cùng trên một đơn vị sản phẩm (Gram hoặc Món) dùng để quản lý kho và định giá bán lẻ:





$$\\text{Đơn giá vốn} = \\frac{\\text{Tổng tiền} - \\text{Chiết khấu phân bổ}}{\\text{Số món}}$$





Hoặc tính tổng giá trị vốn sau chiết khấu trước rồi chia cho Số món:





$$\\text{Đơn giá vốn} = \\frac{\\text{Tổng tiền sau chiết khấu}}{\\text{Số món}}$$



3\. KHỚP NỐI VÀ ĐỐI CHIẾU DỮ LIỆU THỰC TẾ (EXCEL INFERENCE)



Dựa trên dữ liệu thực tế tại ảnh {0517DE04-496A-41B3-B62F-B1F5574E7D96}.png, Chatbot phân tích 2 kịch bản hóa đơn sau:



Kịch bản 1: Toa hàng KHÔNG có Chiết khấu phân bổ (Nửa trên bảng tính)



Dòng 1 (Vàng 750 gr):



Số món = 10 | Đơn giá = 1.780.000 $\\rightarrow$ Thành tiền = 17.800.000.



Chi phí phát sinh = 100.000 (Phí chứng từ) + 50.000 (Phí khác 1) = 150.000.



Chiết khấu phân bổ = 0 (Không có).



Tổng tiền = 17.800.000 + 150.000 = $\\mathbf{17.950.000}$.



ĐG vốn = $17.950.000 / 10 = \\mathbf{1.795.000}$ (Khớp hoàn toàn cột N).



Kịch bản 2: Toa hàng CÓ Chiết khấu phân bổ (Nửa dưới bảng tính)



Hóa đơn này được NCC áp dụng gói Tổng chiết khấu là 500.000 VND cho tổng toa gồm 34 món.



Phân bổ chiết khấu:



$\\text{Giá món chiết khấu} = 500.000 / 34 = \\mathbf{14.705,88235 \\text{ VND/món}}$.



Áp dụng tính toán cho Dòng 1 (Số món = 10):



Chiết khấu phân bổ = $14.705,88235 \\times 10 = \\mathbf{147.058,8235 \\text{ VND}}$ (Khớp ô L18).



Tổng tiền trước chiết khấu = 17.950.000.



Tổng tiền sau chiết khấu = 17.950.000 - 147.058,8235 = $\\mathbf{17.802.941,1765 \\text{ VND}}$ (Khớp ô M18).



ĐG vốn = $17.802.941,1765 / 10 = \\mathbf{1.780.294,1176 \\text{ VND}}$ (Khớp ô N18).

