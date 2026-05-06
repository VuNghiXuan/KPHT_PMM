
# apps/excel_miner/admin.py
from django.shortcuts import render

def system_map_view(request):
    # Trả về file html có các Tab mà anh đã soạn
    return render(request, 'admin/system_map.html')