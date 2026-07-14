"""
File: apps/subscriptions/views.py
Mô tả: Xử lý logic nâng cấp gói dịch vụ cho Công ty.
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import SubscriptionPlan

@login_required
def upgrade_plan_view(request, plan_id):
    """
    Xử lý yêu cầu nâng cấp gói dịch vụ từ Dashboard.
    
    Args:
        request: HTTP Request.
        plan_id (int): ID của gói dịch vụ muốn nâng cấp lên.
    """
    new_plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
    company = request.user.profile.company
    
    with transaction.atomic():
        # Cập nhật gói dịch vụ cho công ty
        company.plan = new_plan
        company.save()
        
        # Ghi log thành công
        messages.success(request, f"Chúc mừng! Bạn đã nâng cấp thành công lên gói {new_plan.name}.")
    
    return redirect('dashboard')