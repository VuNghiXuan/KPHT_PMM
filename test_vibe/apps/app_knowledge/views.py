# apps/app_knowledge/views.py
from django.shortcuts import render, get_object_or_404
from .models import KnowledgeDraft
from apps.app_miner.models import DataSource

def agent_workflow_map(request, project_id):
    project = get_object_or_404(DataSource, pk=project_id)
    drafts = KnowledgeDraft.objects.filter(project_id=project_id)
    
    stats = {
        'total': drafts.count(),
        'ready': drafts.filter(status='AI_READY').count(),
        'pending': drafts.filter(status='PENDING').count(),
        'edited': drafts.filter(status='EDITED').count(),
    }

    # Lấy danh sách DataType - Nếu chưa có thì dùng mặc định để tránh lỗi Mermaid
    data_types = list(drafts.exclude(data_type__isnull=True).values_list('data_type__name', flat=True).distinct())
    
    if not data_types:
        # Dự phòng khi chưa có DataType nào được gán
        dt_nodes = "Default_Node"
        dt_definitions = "Default_Node[Nghiệp vụ chung]"
    else:
        # Tạo ID node an toàn (không dấu, không cách)
        dt_nodes = " & ".join([f"DT_{i}" for i in range(len(data_types))])
        dt_definitions = "\n        ".join([f"DT_{i}[{name}]" for i, name in enumerate(data_types)])

    # Chuỗi Mermaid - Đã bọc kỹ để tránh lỗi cú pháp
    mermaid_graph = f"""
    graph TD
        Start(📂 {project.name}: {stats['total']} Sheets) --> Scan[🔍 Quét Metadata]
        Scan --> Logic{{🧠 Scoring System}}
        
        subgraph "Phân loại nghiệp vụ"
        {dt_definitions}
        end

        Logic --> {dt_nodes}
        {dt_nodes} --> AI[[🤖 AI Agent Core]]
        
        AI --> Result{{Kết quả xử lý}}
        
        Result -->|Xong| Ready[✅ AI_READY: {stats['ready']}]
        Result -->|Sửa| Edited[📝 EDITED: {stats['edited']}]
        Result -->|Chờ| Help[⚠️ PENDING: {stats['pending']}]
        
        style Ready fill:#2ecc71,stroke:#27ae60,color:#fff
        style Edited fill:#e67e22,stroke:#d35400,color:#fff
        style Help fill:#e74c3c,stroke:#c0392b,color:#fff
        style AI fill:#9b59b6,stroke:#8e44ad,color:#fff
        style Start fill:#34495e,stroke:#2c3e50,color:#fff
    """
    
    return render(request, 'admin/app_knowledge/agent_map.html', {
        'mermaid_graph': mermaid_graph.strip(), # strip để bỏ dòng trống thừa
        'project': project
    })