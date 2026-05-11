from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

# Dùng decorator này để đảm bảo chỉ có admin/staff mới xem được bản đồ
@staff_member_required
def system_map_view(request):
    """
    Xử lý hiển thị bản đồ quy trình hệ thống HTJ
    """
    context = {
        'title': 'Bản đồ quy trình hệ thống Ứng Dụng Vàng',
        # Anh có thể truyền thêm dữ liệu từ database vào đây nếu cần
    }
    return render(request, 'admin/system_map.html', context)