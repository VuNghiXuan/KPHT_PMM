"""
File: apps/subscriptions/views.py
Mục đích: Xử lý logic quản lý gói dịch vụ và nâng cấp cho Tenant.
"""
from django.views.generic import ListView
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import SubscriptionPlan

class SubscriptionListView(ListView):
    """
    Class hiển thị danh sách các gói dịch vụ có sẵn.
    
    Kế thừa từ: django.views.generic.ListView
    """
    model = SubscriptionPlan
    template_name = 'subscriptions/plan_list.html'
    context_object_name = 'plans'

    def get_queryset(self):
        # Trả về các gói dịch vụ đang hoạt động
        return SubscriptionPlan.objects.filter(is_active=True)

@login_required
def upgrade_plan_view(request, plan_id: int):
    """
    Xử lý logic nâng cấp gói dịch vụ cho Công ty.
    """
    new_plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
    company = request.user.profile.company
    
    with transaction.atomic():
        company.plan = new_plan
        company.save()
        messages.success(request, f"Chúc mừng! Bạn đã nâng cấp lên gói {new_plan.name}.")
    
    return redirect('dashboard')