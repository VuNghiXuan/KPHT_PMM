# apps/subscriptions/utils.py
"""
Middleware hoặc Decorator để chặn quyền
Để đảm bảo người dùng không thể truy cập URL nếu gói dịch vụ không hỗ trợ, bạn hãy tạo một Decorator.
"""

from django.core.exceptions import PermissionDenied
from functools import wraps

def feature_required(feature_slug):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Lấy thông tin công ty từ user đã đăng nhập
            company = request.user.profile.company
            
            # 2. Kiểm tra xem gói dịch vụ của công ty có chứa feature_slug không
            # Giả định SubscriptionPlan có quan hệ ManyToMany với Feature
            if company.plan and company.plan.features.filter(slug=feature_slug).exists():
                return view_func(request, *args, **kwargs)
            
            # 3. Nếu không có quyền, chặn lại
            raise PermissionDenied("Gói dịch vụ của công ty bạn không bao gồm tính năng này.")
        return _wrapped_view
    return decorator