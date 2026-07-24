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


class SystemBlueprintView(View):
    """
    Class: SystemBlueprintView
    Inherits: django.views.View
    Description: 
        View quản lý Living Documentation, thực hiện nội soi mã nguồn qua 
        ArchitectureIntrospectionEngine và in debug chuỗi sơ đồ ra Terminal để rà soát.
    """
    
    def get(self, request, *args, **kwargs):
        """
        Xử lý phương thức GET, gọi engine sinh sơ đồ và in log debug chi tiết 
        giúp kỹ sư phát hiện nhanh nguyên nhân lỗi cú pháp Mermaid hoặc dữ liệu trống.
        """
        code_flow = ArchitectureIntrospectionEngine.generate_code_flow()
        dynamic_erd = ArchitectureIntrospectionEngine.generate_erd()
        state_machine = ArchitectureIntrospectionEngine.generate_state_machine()
        component_diagram = ArchitectureIntrospectionEngine.generate_component_diagram()

        # --- DEBUG PRINTS CHO KỸ SƯ ---
        # print("\n" + "="*60)
        # print(" [DEBUG ARCHITECTURE ENGINE INTROSPECTION RUNNING] ")
        # print("="*60)
        # print(f"-> Code Flow Length: {len(code_flow)} chars")
        # print(f"-> Dynamic ERD Length: {len(dynamic_erd)} chars")
        # print("--- [DYNAMIC ERD CONTENT PREVIEW] ---")
        # print(dynamic_erd[:400] if dynamic_erd else "⚠️ ERD is Empty!")
        # print("---------------------------------------")
        # print(f"-> State Machine Length: {len(state_machine)} chars")
        # print(f"-> Component Diagram Length: {len(component_diagram)} chars")
        # print("="*60 + "\n")

        context = {
            'code_flow': code_flow,
            'dynamic_erd': dynamic_erd,
            'state_machine': state_machine,
            'component_diagram': component_diagram,
        }
        return render(request, 'arch_manager/sys_blue_print.html', context)


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