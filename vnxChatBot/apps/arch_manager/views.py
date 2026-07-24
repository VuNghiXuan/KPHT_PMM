"""
Module: arch_manager.views
Author: Senior Software Engineer & Architecture Lead
Description: View điều khiển Living Documentation, tự động nội soi code 
             để dựng 4 sơ đồ trực quan, hỗ trợ debug lỗi Mermaid và phê duyệt kiến trúc.
"""

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .utils import ArchitectureIntrospectionEngine
from .models import SystemBlueprint
import datetime
from django.http import HttpResponse
from .utils_manifest import get_vnx_manifest # Hoặc hàm gom manifest của bạn
import os

class SystemBlueprintView(View):
    """
    Class: SystemBlueprintView
    Inherits: django.views.View
    Description: 
        View quản lý Living Documentation, thực hiện nội soi mã nguồn qua 
        ArchitectureIntrospectionEngine và Project Manifest để dựng giao diện trực quan.
    """
    
    def get(self, request, *args, **kwargs):
        code_flow = ArchitectureIntrospectionEngine.generate_code_flow()
        dynamic_erd = ArchitectureIntrospectionEngine.generate_erd()
        state_machine = ArchitectureIntrospectionEngine.generate_state_machine()
        component_diagram = ArchitectureIntrospectionEngine.generate_component_diagram()
        
        # Gọi hàm lấy nội dung manifest toàn bộ dự án (đã chuyển markdown sang html an toàn hoặc hiển thị text dạng pre)
        # from .utils_manifest import get_vnx_manifest # Hoặc hàm gom manifest của bạn
        # import os
        project_manifest = get_vnx_manifest(os.getcwd())

        context = {
            'code_flow': code_flow,
            'dynamic_erd': dynamic_erd,
            'state_machine': state_machine,
            'component_diagram': component_diagram,
            'project_manifest': project_manifest,
        }
        # print('================project_manifest', project_manifest)
        return render(request, 'arch_manager/sys_blue_print.html', context)


@staff_member_required
def download_project_manifest(request):
    """
    Function: download_project_manifest
    Description: Tự động nội soi cấu trúc dự án và trả về tệp VNX_PROJECT_MANIFEST.md 
                 để kỹ sư hoặc AI tải về làm tài liệu ngữ cảnh học tập.
    """
    root_dir = os.getcwd()
    manifest_content = get_vnx_manifest(root_dir)
    
    response = HttpResponse(manifest_content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="VNX_PROJECT_MANIFEST.md"'
    return response


@staff_member_required
def approve_system_blueprint(request):
    """
    Function: approve_system_blueprint
    Description: Lưu lại trạng thái bản thiết kế hiện tại và kích hoạt phiên bản kiến trúc mới.
    """
    if request.method == 'POST':
        try:
            code_flow = ArchitectureIntrospectionEngine.generate_code_flow()
            dynamic_erd = ArchitectureIntrospectionEngine.generate_erd()
            state_machine = ArchitectureIntrospectionEngine.generate_state_machine()
            component_diagram = ArchitectureIntrospectionEngine.generate_component_diagram()

            # Vô hiệu hóa các bản cũ
            SystemBlueprint.objects.all().update(is_active=False)

            # Tạo bản ghi snapshot mới được duyệt
            version_tag = f"v1.0.{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
            
            SystemBlueprint.objects.create(
                version=version_tag,
                title=f"Tự động cập nhật kiến trúc {version_tag}",
                code_flow_mermaid=code_flow,
                erd_mermaid=dynamic_erd,
                state_machine_mermaid=state_machine,
                component_mermaid=component_diagram,
                description="Đồng bộ hóa tự động từ Living Documentation Engine.",
                is_active=True
            )

            messages.success(request, f"Đã duyệt và lưu phiên bản kiến trúc ({version_tag}) thành công!")
        except Exception as e:
            messages.error(request, f"Lỗi khi lưu phiên bản kiến trúc: {str(e)}")
            
    return redirect('arch_manager:blueprint_dashboard')