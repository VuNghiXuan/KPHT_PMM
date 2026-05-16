## 1. Thiết Lập Môi Trường Ảo (Virtual Environment)
Trong Python, mỗi dự án nên nằm trong một "cái lồng" riêng để không làm ảnh hưởng đến các ứng dụng khác.

*   **Bước 1:** Mở Terminal (CMD hoặc PowerShell) tại thư mục dự án của bạn.
*   **Bước 2:** Tạo môi trường ảo:
    ```bash
    python -m venv env
    ```
*   **Bước 3:** Kích hoạt môi trường:
    *   **Windows:** `env\Scripts\activate`
    *   **Mac/Linux:** `source env/bin/activate`

> **Ghi chú:** Khi thấy chữ `(env)` hiện ở đầu dòng lệnh, nghĩa là bạn đã thành công.

---

## 2. Cài Đặt Django Bằng Pip
Pip là trình quản lý thư viện của Python. Chúng ta sẽ dùng nó để tải Django về.

*   **Lệnh cài đặt:**
    ```bash
    pip install django
    ```
*   **Kiểm tra phiên bản:**
    ```bash
    python -m django --version
    ```

---

## 3. Khởi Tạo Dự Án (Project)
Dự án (Project) là trung tâm điều khiển chứa các cấu hình quan trọng nhất.

*   **Lệnh khởi tạo:**
    ```bash
    django-admin startproject core .
    ```
    *(Dấu chấm `.` ở cuối rất quan trọng, nó giúp Django tạo file ngay tại thư mục hiện tại thay vì tạo thêm một thư mục con lồng nhau).*

---

## 4. Tạo Ứng Dụng (App) Trong Thư Mục `apps/`
Để dự án gọn gàng, chúng ta quy định tất cả các tính năng (như quản lý vàng, hướng dẫn chatbot) sẽ nằm trong thư mục `apps/`.

*   **Bước 1:** Tạo thư mục chứa app:
    ```bash
    mkdir apps
    ```
*   **Bước 2:** Di chuyển vào thư mục apps và tạo app mới:
    ```bash
    cd apps
    python ../manage.py startapp my_new_app
    cd ..
    ```
    *(Lưu ý: `../manage.py` được dùng vì file `manage.py` đang nằm ở thư mục cha).*

---

## 5. Khai Báo App Trong Cấu Hình (Settings)
Sau khi tạo App, bạn phải "giới thiệu" nó với Project để Django nhận diện.

*   Mở file `core/settings.py` (hoặc `settings.py` của bạn).
*   Tìm danh sách `INSTALLED_APPS` và thêm đường dẫn app vào:
```python
INSTALLED_APPS = [
    ...
    'apps.my_new_app', # Khai báo đường dẫn đầy đủ từ thư mục gốc
    ...
]---

## 7. Đồng Bộ Database (Migrations)
Mỗi khi bạn thay đổi file `models.py`, bạn phải cập nhật Database thông qua 2 lệnh "thần thánh":

1.  **Ghi nhận thay đổi:**
    ```bash
    python manage.py makemigrations
    ```
2.  **Thực thi thay đổi vào Database:**
    ```bash
    python manage.py migrate
    ```

---

## 8. Tạo Giao Diện Quản Trị (User Admin)
Django cung cấp sẵn một trang quản lý cực kỳ mạnh mẽ. Để sử dụng, bạn cần một tài khoản "Sếp".

*   **Lệnh tạo tài khoản:**
    ```bash
    python manage.py createsuperuser
    ```
    *(Nhập Username, Email và mật khẩu. Lưu ý: Khi gõ mật khẩu, màn hình sẽ không hiện ký tự, bạn cứ gõ bình thường rồi Enter).*

*   **Đăng ký Model vào Admin:** Mở `apps/my_new_app/admin.py`:
    ```python
    from django.contrib import admin
    from .models import GoldType

    admin.site.register(GoldType)
    ```

---

## 9. Cấu Hình Đường Dẫn (URLs)
Để người dùng truy cập được trang web, bạn cần định nghĩa đường dẫn.

*   **Tại App (`apps/my_new_app/urls.py`):**
    ```python
    from django.urls import path
    from . import views

    urlpatterns = [
        path('', views.home, name='home'),
    ]
    ```
*   **Tại Project (`core/urls.py`):**
    ```python
    from django.urls import path, include

    urlpatterns = [
        path('admin/', admin.site.urls),
        path('gold/', include('apps.my_new_app.urls')),
    ]
    ```

---

## 10. Khởi Động Server Và Kiểm Tra
Cuối cùng, hãy tận hưởng thành quả của bạn!

*   **Lệnh chạy server:**
    ```bash
    python manage.py runserver
    ```
*   **Địa chỉ truy cập:**
    *   Trang chủ: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
    *   Trang quản trị: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

### 💡 Những Quy Tắc "Sống Còn" Cho Người Mới:
1.  **Luôn luôn** kiểm tra xem đã kích hoạt `(env)` chưa trước khi code.
2.  **Mọi thay đổi** ở `models.py` đều phải đi kèm với `makemigrations` và `migrate`.
3.  **Lỗi Namespace:** Nếu bạn để app trong thư mục `apps/`, hãy nhớ luôn gọi `apps.ten_app` thay vì chỉ gọi `ten_app`.
4.  **Thụt lề:** Python rất quan trọng việc thụt lề (4 dấu cách), hãy đảm bảo code của bạn thẳng hàng.

---
*Tài liệu hướng dẫn nội bộ - Hệ thống ChatBot Kim Phát Hiệp Thành.*

---

Anh Vũ chỉ cần copy đoạn này vào mục **Nội dung hướng dẫn** trong trang Admin của anh. Với cấu hình `Safe` và `Markdown` mà anh em mình vừa làm, trang Wiki của anh sẽ hiện ra cực kỳ rõ ràng, giúp nhân viên mới nhìn vào là biết làm ngay.

Anh thấyChào anh **Vũ**, để giúp người mới (như team của anh) có một tài liệu "gối đầu giường" đầy đủ, trình bày đẹp mắt trên giao diện Wiki mà anh em mình vừa dựng, em đã viết lại toàn bộ lộ trình cài đặt Django. 

Nội dung này được tối ưu hóa chuẩn Markdown để khi đi qua bộ lọc `markdown_format` anh vừa cài, nó sẽ hiển thị chuyên nghiệp với đầy đủ các khối code, ghi chú và tiêu đề rõ ràng.

---

# 🚀 Lộ Trình Toàn Diện: Từ Cài Đặt Đến Vận Hành Dự Án Django

Chào mừng bạn đến với thế giới của **Django** – Framework web mạnh mẽ giúp bạn xây dựng các hệ thống quản lý chuyên nghiệp như dự án **Kim Phát Hiệp Thành**. Tài liệu này hướng dẫn chi tiết từng bước để bạn từ số 0 trở thành người có thể vận hành một ứng dụng Django hoàn chỉnh.

---