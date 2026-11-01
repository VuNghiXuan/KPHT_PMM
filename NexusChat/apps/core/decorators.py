# apps/core/decorators.py
from django.shortcuts import redirect
from functools import wraps

def profile_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'profile'):
            return view_func(request, *args, **kwargs)
        return redirect('core:profile-setup') # Chỉ chặn khi họ truy cập đúng trang kế toán
    return _wrapped_view