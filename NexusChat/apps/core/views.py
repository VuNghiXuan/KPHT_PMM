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
                basic_plan = SubscriptionPlan.objects.get(slug='basic') 
                company = Company.objects.create(
                    name=form.cleaned_data['company_name'],
                    tax_code=form.cleaned_data['tax_code'],
                    plan=basic_plan
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


@login_required(login_url='core:login')

def dashboard_view(request):
    """
    Hiển thị bảng điều khiển. Yêu cầu người dùng phải đăng nhập.
    """
    # Bây giờ, request.user chắc chắn là một đối tượng User thực (không phải AnonymousUser)
    if not request.user.has_profile:
        return redirect('core:profile-setup')
    
    # Lấy toàn bộ gói dịch vụ từ database
    all_plans = SubscriptionPlan.objects.all()
    
    context = {
        'all_plans': all_plans,
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