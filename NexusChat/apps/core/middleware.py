from django.utils.deprecation import MiddlewareMixin
from threading import local

# Dùng local để lưu dữ liệu riêng biệt cho mỗi luồng xử lý request
_thread_locals = local()

def get_current_company():
    """
    Hàm này được gọi từ bất cứ đâu (Model, View, Form) 
    để lấy công ty của user hiện tại mà không cần truyền request object.
    """
    return getattr(_thread_locals, 'company', None)

class CompanyMiddleware(MiddlewareMixin):
    """
    Middleware chặn mọi request để xác định công ty của User.
    """
    def process_request(self, request):
        # 1. Kiểm tra User đã đăng nhập chưa
        if request.user.is_authenticated:
            try:
                # 2. Gán company vào biến thread-local để dùng toàn cục
                _thread_locals.company = request.user.profile.company
            except AttributeError:
                # Nếu User chưa có Profile (ví dụ: Admin chưa gắn công ty)
                _thread_locals.company = None
        else:
            _thread_locals.company = None