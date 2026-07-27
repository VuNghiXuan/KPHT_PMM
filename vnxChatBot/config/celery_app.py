"""
celery_app là một instance (thực thể) của ứng dụng Celery được khởi tạo sẵn trong dự án (thường nằm ở file vnxChatBot/celery.py). 
Nó đóng vai trò là "trạm điều phối" trung tâm, giúp kết nối Django với môi trường chạy ngầm (Broker như Redis) để thực thi các tác vụ bất đồng bộ (như xử lý file nặng, quét vector tài liệu RAG) mà không làm đơ giao diện web chính.
"""
# vnxChatBot\celery_app.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('vnxChatBot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

"""
celery -A config.celery_app worker --pool=solo -l info
Lệnh celery -A config.celery_app worker --pool=solo -l info dùng để làm gì?
Đây là lệnh dùng để khởi động một Celery Worker trên máy của bạn nhằm lắng nghe và thực thi các tác vụ ngầm đang chờ trong hàng đợi Redis:
Lệnh celery -A config.celery_app worker --pool=solo -l info dùng để làm gì?
Đây là lệnh dùng để khởi động một Celery Worker trên máy của bạn nhằm lắng nghe và thực thi các tác vụ ngầm đang chờ trong hàng đợi Redis:

-A vnxChatBot: Chỉ định ứng dụng Django/Celery chính mà worker cần quản lý (ở đây project tên là vnxChatBot).

worker: Khởi động tiến trình worker chuyên nhận và xử lý task.

--pool=solo: Ép worker chạy ở chế độ đơn luồng (solo pool) thay vì đa tiến trình (multiprocessing). Đây là điểm cực kỳ quan trọng khi chạy trên hệ điều hành Windows, giúp tránh triệt để các lỗi xung đột tiến trình (PicklingError, PermissionError hoặc lỗi không nhận diện task) hay gặp trên Windows.

-l info: Đặt mức độ log (log level) ở dạng INFO để hiển thị chi tiết các dòng thông báo trạng thái, giúp bạn dễ dàng theo dõi task nào đang chạy, thành công hay thất bại ngay trên màn hình Terminal.
"""