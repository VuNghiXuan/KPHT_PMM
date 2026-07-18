"""
Mục đích: Xử lý xác thực người dùng và điều hướng chính.
Tác giả: Kiến trúc sư VnxChatBot
Lưu ý: Đã loại bỏ hoàn toàn Company/Profile model cũ. Sử dụng ChatGroup làm đơn vị tenant.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from apps.group_chat.models import ChatGroup, Membership
from .forms_register import RegistrationForm

@csrf_protect
def register_view(request):
    """
    Đăng ký người dùng mới. Sau khi đăng ký, user tự tạo nhóm hoặc tham gia nhóm.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Đăng nhập và chuyển hướng đến trang tạo nhóm đầu tiên
            login(request, user)
            return redirect('group_chat:create_group') 
    else:
        form = RegistrationForm()
    return render(request, 'registration.html', {'form': form})

@login_required
def dashboard_view(request):
    """
    Dashboard hiển thị các nhóm mà người dùng đang tham gia.
    """
    # Lấy danh sách các nhóm thông qua Membership
    my_memberships = Membership.objects.filter(user=request.user).select_related('group')
    my_groups = [m.group for m in my_memberships]
    
    context = {
        'my_groups': my_groups,
        'chart_labels': ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'],
        'chart_data': [120, 150, 180, 200, 240, 280, 310, 350, 380, 410, 450, 480]
    }
    return render(request, 'dashboard.html', context)