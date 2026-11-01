from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.db import transaction, IntegrityError
from django.contrib import messages
from .models import Company, Profile
from apps.subscriptions.models import SubscriptionPlan
from .forms_register import RegistrationForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from .forms_profile_customer import ProfileSetupForm # Giả sử bạn đã có form này
from django.views.decorators.csrf import csrf_protect
from apps.group_chat.models import ChatGroup #



def debug_auth_config(request):
    print(f"DEBUG: LOGIN_URL config is: {settings.LOGIN_URL}")
    try:
        url = reverse('core:login')
        print(f"DEBUG: Resolved core:login to: {url}")
    except Exception as e:
        print(f"DEBUG: Could not resolve core:login - {e}")


@csrf_protect
@transaction.atomic
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                # 1. Tạo User
                user = form.save(commit=False) # Nếu form là ModelForm
                user.set_password(form.cleaned_data['password'])
                user.save()
                
                # 2. Tạo Công ty (Dùng slug thay vì ID)
                # Giả sử bạn có slug='basic' cho gói cơ bản
                basic_plan = SubscriptionPlan.objects.filter(slug='basic').first() 
                company = Company.objects.create(
                    name=form.cleaned_data['company_name'],
                    tax_code=form.cleaned_data['tax_code'],
                    plan=basic_plan # Có thể là None nếu không tìm thấy gói
                )
                
                # 3. Tạo Profile
                Profile.objects.create(user=user, company=company)
                
                # 4. Đăng nhập luôn
                login(request, user)
                return redirect('dashboard') 
                
            except IntegrityError:
                messages.error(request, "Có lỗi xảy ra, có thể mã số thuế đã tồn tại.")
                return render(request, 'registration.html', {'form': form})
    else:
        form = RegistrationForm()
    return render(request, 'registration.html', {'form': form})


# @login_required(login_url='core:login')
# def dashboard_view(request):
#     user_profile = getattr(request.user, 'profile', None)
#     all_plans = SubscriptionPlan.objects.all()
#     # Nhóm chat lấy theo user, không cần điều kiện profile
#     my_groups = ChatGroup.objects.filter(members=request.user) 
    
#     context = {
#         'user_profile': user_profile,
#         'all_plans': all_plans,
#         'my_groups': my_groups,
#     }
#     return render(request, 'dashboard.html', context)

@login_required(login_url='core:login')
def dashboard_view(request):
    """
    Hiển thị trang Dashboard với dữ liệu thống kê nhóm và các gói dịch vụ.
    
    Returns:
        Rendered template 'dashboard.html' với context đầy đủ.
    """
    user = request.user
    user_profile = getattr(user, 'profile', None)
    all_plans = SubscriptionPlan.objects.all()
    my_groups = ChatGroup.objects.filter(members=user) 
    
    # Dữ liệu giả lập cho biểu đồ (Trong tương lai sẽ truy vấn từ Model Message/Document)
    context = {
        'user_profile': user_profile,
        'all_plans': all_plans,
        'my_groups': my_groups,
        'chart_labels': ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'],
        'chart_data': [120, 150, 180, 200, 240, 280, 310, 350, 380, 410, 450, 480]
    }
    return render(request, 'dashboard.html', context)


@login_required
def profile_setup_view(request):
    """
    Xử lý thiết lập profile. 
    - Nếu đã có profile: Chuyển thẳng về Dashboard.
    - Nếu là Superuser: Có thể cho phép bỏ qua hoặc ép buộc thiết lập (tùy nhu cầu).
    """
    
    # 1. Kiểm tra nếu đã có profile thì không cần thiết lập lại
    if hasattr(request.user, 'profile'):
        return redirect('dashboard')

    # 2. Xử lý logic thiết lập
    if request.method == 'POST':
        form = ProfileSetupForm(request.POST)
        if form.is_valid():
            form.save(user=request.user)
            return redirect('dashboard')
    else:
        form = ProfileSetupForm()
        
    return render(request, 'core/profile_setup.html', {
        'form': form,
        'is_superuser': request.user.is_superuser
    })



@login_required
def company_list_view(request):
    # Lấy danh sách công ty mà user có quyền truy cập
    companies = Company.objects.filter(profile__user=request.user)
    return render(request, 'core/company_list.html', {'companies': companies})