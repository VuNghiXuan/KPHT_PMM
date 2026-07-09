# apps/core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import Company, Profile
from apps.subscriptions.models import SubscriptionPlan
from .forms_register import RegistrationForm
from django.db import transaction

from django.contrib.auth.decorators import login_required

@transaction.atomic
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # 1. Tạo User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            
            # 2. Tạo Công ty và gán Gói Cơ Bản (ID=1)
            basic_plan = SubscriptionPlan.objects.get(id=1) 
            company = Company.objects.create(
                name=form.cleaned_data['company_name'],
                tax_code=form.cleaned_data['tax_code'],
                plan=basic_plan
            )
            
            # 3. Tạo Profile kết nối User với Công ty
            Profile.objects.create(user=user, company=company)
            
            return redirect('/admin/') # Chuyển hướng đến trang quản trị
    else:
        form = RegistrationForm()
    return render(request, 'registration.html', {'form': form})

@login_required
def dashboard_view(request):
    # Logic: Template sẽ tự lấy allowed_features từ context_processors
    return render(request, 'dashboard.html')