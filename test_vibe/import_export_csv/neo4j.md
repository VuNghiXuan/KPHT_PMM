# HƯỚNG DẪN CÀI ĐẶT NEO4J CHO DỰ ÁN CHATBOT HTJ

Tài liệu này hướng dẫn cài đặt Neo4j Database để phục vụ lưu trữ tri thức đồ thị (Graph Knowledge) cho hệ thống quản lý tiệm vàng.

---

## 1. Yêu cầu hệ chuẩn bị
*   Đã cài đặt **Docker Desktop** (Khuyên dùng để giữ máy sạch và dễ quản lý).
*   Đã kích hoạt **WSL2** (nếu dùng Windows).

## 2. Cài đặt bằng Docker (Cách nhanh nhất)

Mở Terminal (CMD hoặc PowerShell) và chạy lệnh sau để tạo Container Neo4j. 

> **Lưu ý:** Thay `password_cua_anh_vu` bằng mật khẩu thực tế của anh.
>Khởi động docker destop sau khi thành công thì mới nhập ở môi trường ảo

```bash
docker run --name neo4j_kpht -p 7474:7474 -p 7687:7687 -d --env NEO4J_AUTH=neo4j/kpht2026 neo4j:latest
```
> Sau khi chạy lệnh này, nếu thành công, nó sẽ trả về một dãy số dài (ID của Container).

Anh đợi khoảng 30 giây cho hệ thống khởi động.

Mở trình duyệt gõ: http://localhost:7474.

Đăng nhập với mật khẩu: kpht2026.

Giải thích các cổng kết nối:
7474: Cổng truy cập giao diện quản lý (Neo4j Browser).

7687: Cổng kết nối dữ liệu Bolt (Dùng cho Django/Python).

## 3. Cấu hình vào Dự án Django
Bước 1: Cài đặt thư viện kết nối
Trong môi trường ảo (env), anh chạy lệnh:

```bash
pip install django-neomodel
```

Bước 2: Cập nhật core/settings.py
Thêm cấu hình kết nối Neo4j vào file settings để Django có thể nhận diện:

```python
# Cấu hình Neo4j cho Ứng Dụng Vàng
# --- NEO4J CONFIGURATION FOR Ứng Dụng Vàng LOCAL:---
# Định dạng: bolt://<username>:<password>@<host>:<port>
NEO4J_URL=bolt://neo4j:kpht2026@localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=kpht2026

## 4. Kiểm tra và Sử dụng
Truy cập Giao diện: Mở trình duyệt và truy cập http://localhost:7474.

Đăng nhập:

Username: neo4j

Password: password_cua_anh_vu (Mật khẩu anh đã đặt ở Bước 2).

Giao diện Cypher: Đây là nơi anh có thể viết các câu lệnh truy vấn đồ thị để kiểm tra các Node dữ liệu từ ExcelMiner đổ lên.

## 5. Các lệnh Docker hữu ích
Dừng Neo4j: docker stop neo4j_kpht

Chạy lại Neo4j: docker start neo4j_kpht

Xem Log lỗi: docker logs -f neo4j_kpht

Ghi chú: Sau khi cài đặt xong, bước tiếp theo chúng ta sẽ triển khai graph_syncer.py để đồng bộ DataField từ MySQL sang Neo4j.
---

### Mẹo cho anh Vũ:
Nếu sau này anh muốn con AI của mình mạnh hơn, anh có thể cài thêm Plugin **APOC** cho Neo4j. Nhưng trước mắt, cứ cài bản thuần này là đủ để bóc tách toàn bộ logic tính toán của tiệm vàng!