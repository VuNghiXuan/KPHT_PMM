# apps/accounting/views.py
from django.shortcuts import render, HttpResponse
from apps.subscriptions.utils import feature_required
from apps.core.views import login_required, profile_required

# Giả lập view báo cáo
@feature_required('financial-reports')
def financial_report_view(request):
    # Logic giả lập: Trả về nội dung đơn giản
    return HttpResponse("<h1>Chào mừng bạn đến với App Báo cáo tài chính!</h1><p>Bạn đã có quyền truy cập.</p>")

# apps/accounting/views.py
@login_required
@profile_required # CHỈ VIEW NÀY CẦN PROFILE
def accounting_dashboard(request):
    return render(request, 'accounting/dashboard.html')