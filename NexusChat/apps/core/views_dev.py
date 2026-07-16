import os
import ast
from django.shortcuts import render
from django.apps import apps
from django.conf import settings
from django.http import HttpResponse

# Mô tả nghiệp vụ cố định
APP_DESC = {
    "core": "Nền tảng xác thực, quản lý Profile và Tenant (Company).",
    "group_chat": "Quản lý ChatGroup, Membership và tin nhắn (WebSocket).",
    "ai_assistant": "AI Brain, RAG Engine, tích hợp LLM và Vector Store.",
    "subscriptions": "Quản lý gói dịch vụ và phân quyền tính năng."
}

def get_manifest_content(root_dir):
    manifest = ["# NexusChat Project Manifest", f"> *Cập nhật lần cuối: {os.popen('date /t').read().strip()}*"]
    apps_path = os.path.join(root_dir, 'apps')
    
    if not os.path.exists(apps_path):
        return "# NexusChat Project Manifest\nLỗi: Không tìm thấy thư mục apps."

    app_dirs = [d for d in os.listdir(apps_path) if os.path.isdir(os.path.join(apps_path, d)) and not d.startswith('__')]
    
    manifest.append("\n## 1. Hệ thống Modules (Apps)")
    for app in app_dirs:
        desc = APP_DESC.get(app, "Chưa có mô tả nghiệp vụ")
        manifest.append(f"- **{app}**: {desc}")
    
    manifest.append("\n## 2. Bản đồ Class & Luồng (Tự động hóa)")
    for app in app_dirs:
        app_path = os.path.join(apps_path, app)
        manifest.append(f"\n### App: {app}")
        
        # Đọc README.md
        readme = os.path.join(app_path, 'README.md')
        if os.path.exists(readme):
            with open(readme, 'r', encoding='utf-8') as f:
                manifest.append(f"#### Mô tả chi tiết:\n{f.read().strip()}\n")

        # Đọc models, views, services
        for file in ['models.py', 'views.py', 'services.py']:
            path = os.path.join(app_path, file)
            if os.path.exists(path):
                manifest.append(f"#### File: `{file}`")
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read())
                        doc = ast.get_docstring(tree)
                        if doc: manifest.append(f"*{doc.splitlines()[0]}*")
                        for node in tree.body:
                            if isinstance(node, ast.ClassDef):
                                cls_doc = ast.get_docstring(node) or "Chưa có mô tả"
                                manifest.append(f"- **Class {node.name}**: {cls_doc.splitlines()[0]}")
                    except: pass
    return "\n".join(manifest)

def architecture_dashboard(request):
    mermaid_data = ["graph LR;"] 
    # Cấu hình Mermaid để tự giãn rộng node theo nội dung
    mermaid_data.append("%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 100}}}%%")
    
    all_models = {}
    
    for app in apps.get_app_configs():
        if app.name.startswith('apps.'):
            sub_name = app.name.replace('.', '_')
            mermaid_data.append(f"subgraph {sub_name}")
            
            for model in app.get_models():
                # Dùng ID duy nhất (vd: apps_core_User)
                model_id = f"{sub_name}_{model.__name__}"
                all_models[model.__name__] = model_id
                # Định dạng node: ID["Tên Model"] -> Mermaid sẽ tự căn chỉnh kích thước box
                mermaid_data.append(f'    {model_id}["{model.__name__}"];')
            
            mermaid_data.append("end")
    
    # Vẽ liên kết dùng ID
    for app in apps.get_app_configs():
        if app.name.startswith('apps.'):
            for model in app.get_models():
                model_id = f"{app.name.replace('.', '_')}_{model.__name__}"
                for field in model._meta.get_fields():
                    if (field.many_to_one or field.one_to_one) and hasattr(field, 'related_model'):
                        target_name = field.related_model.__name__
                        if target_name in all_models:
                            mermaid_data.append(f"{model_id} --> {all_models[target_name]};")
    
    return render(request, 'dev/architecture.html', {
        'mermaid_code': "\n".join(mermaid_data),
        'manifest_content': get_manifest_content(settings.BASE_DIR)
    })

def download_manifest(request):
    content = get_manifest_content(settings.BASE_DIR)
    response = HttpResponse(content, content_type='text/markdown')
    response['Content-Disposition'] = 'attachment; filename="PROJECT_MANIFEST.md"'
    return response