"""
Module: arch_manager.urls
Author: Senior Software Engineer & Architecture Lead
Description: Định tuyến URL cho phân hệ quản lý kiến trúc arch_manager, 
             liên kết trực tiếp giao diện Living Documentation với hàm xử lý phê duyệt.
"""

from django.urls import path
from .views import SystemBlueprintView, approve_system_blueprint
from . import views

app_name = 'arch_manager'

urlpatterns = [
    path('', SystemBlueprintView.as_view(), name='blueprint_dashboard'),
    path('approve/', approve_system_blueprint, name='systemblueprint_approve'),
    path('architecture/download-manifest/', views.download_project_manifest, name='download_manifest'),
]