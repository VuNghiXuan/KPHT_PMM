# HƯỚNG DẪN TẠO APP TRONG DJANGO (DỰ ÁN Ứng Dụng Vàng)
python manage.py startapp app_ai_core
. Trường hợp có thư mục apps hoặc muốn dời app_ai_core đi vào thư mục khác thực hiện:
--> Di chuyển nó vào đúng chỗ anh muốn
move app_ai_core apps\

# HƯỚNG DẪN ĐỔI TÊN APP TRONG DJANGO (DỰ ÁN Ứng Dụng Vàng)

Mẹo :
Trong VS Code, anh dùng tổ hợp phím Ctrl + Shift + H, sau đó:

Ô trên gõ: apps.old_app

Ô dưới gõ: apps.new_app

Nhấn Replace All để nó tự động đổi tên ở tất cả mọi file cho nhanh.

Tài liệu này hướng dẫn cách đổi tên một App hiện có trong thư mục `apps/` sang tên mới mà không làm gãy hệ thống.

---

## Bước 1: Đổi tên thư mục vật lý
1. Truy cập vào thư mục `apps/`.
2. Chuột phải vào thư mục App cũ (ví dụ: `old_app`) và chọn **Rename**.
3. Đổi thành tên mới (ví dụ: `new_app`).

## Bước 2: Cập nhật cấu hình App (apps.py)
Mở file `apps/new_app/apps.py` và sửa lại thuộc tính `name` để Django biết đường dẫn mới:

```python
from django.apps import AppConfig

class NewAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Phải bao gồm cả thư mục apps ở đầu
    name = 'apps.new_app' 
    verbose_name = 'Tên Hiển Thị Trên Admin'
## Bước 3: Bước 3: Cập nhật Settings dự án (settings.py)
 Mở file core/settings.py (hoặc file settings chính của dự án), tìm mục INSTALLED_APPS và cập nhật lại đường dẫn:
INSTALLED_APPS = [
    ...
    'apps.new_app', # Thay thế 'apps.old_app'
    ...
]
## Bước 4:
Bước 4: Thay đổi các lệnh Import trong toàn bộ dự án
Đây là bước quan trọng nhất. Anh cần tìm và thay thế (Ctrl + Shift + F trong VS Code) tất cả các dòng import liên quan đến tên cũ:

Từ: from apps.old_app.models import ...

Thành: from apps.new_app.models import ...

Đừng quên kiểm tra các file:

urls.py của dự án và của App.

views.py, admin.py, signals.py.

Các lệnh import models trong các App khác nếu có liên kết.
## Bước 5: Bước 5: Cập nhật Database (Migration)
Nếu App cũ đã có các bảng trong Database, anh cần thực hiện các lệnh sau để tránh lỗi mất liên kết dữ liệu:

Xóa cache Python: Xóa các thư mục __pycache__ nếu cần.

Migration:

Bash
python manage.py makemigrations new_app
python manage.py migrate

*Lưu ý:* Nếu anh muốn đổi cả tên bảng trong Database, hãy dùng lệnh `RENAME TABLE` trong SQL hoặc tạo một bản migration tùy chỉnh (custom migration). Tuy nhiên, thông thường chỉ cần đổi tên App ở mức code là đủ.

## Bước 6: Kiểm tra các Template Tags (Nếu có)
Nếu App của anh có sử dụng `templatetags`, hãy nhớ cập nhật lại lệnh nạp ở đầu file HTML:
- **Từ:** `{% load old_app_tags %}`
- **Thành:** `{% load new_app_tags %}`

---
**Ghi chú cho Team Ứng Dụng Vàng:** Sau khi đổi tên xong, hãy chạy lệnh `python manage.py runserver` để kiểm tra xem hệ thống có báo lỗi `ModuleNotFoundError` ở đâu không.