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
    Middleware xác định công ty của User một cách an toàn.
    """
    def process_request(self, request):
        _thread_locals.company = None  # Reset về None mặc định
        
        if request.user.is_authenticated:
            # Dùng getattr để lấy profile một cách an toàn, tránh lỗi AttributeError
            profile = getattr(request.user, 'profile', None)
            if profile and profile.company:
                _thread_locals.company = profile.company
            else:
                _thread_locals.company = None