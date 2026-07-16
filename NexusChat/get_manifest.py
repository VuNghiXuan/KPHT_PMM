import os
import ast

# Các mô tả nghiệp vụ cố định cho app
APP_DESC = {
    "core": "Nền tảng xác thực, quản lý Profile và Tenant (Company).",
    "group_chat": "Quản lý ChatGroup, Membership và tin nhắn (WebSocket).",
    "ai_assistant": "AI Brain, RAG Engine, tích hợp LLM và Vector Store.",
    "subscriptions": "Quản lý gói dịch vụ và phân quyền tính năng."
}

def get_manifest_content(root_dir):
    manifest = ["# NexusChat Project Manifest\n", f"> *Cập nhật lần cuối: {os.popen('date /t').read().strip()}*\n"]
    apps_path = os.path.join(root_dir, 'apps')
    
    if not os.path.exists(apps_path):
        return "# NexusChat Project Manifest\nLỗi: Không tìm thấy thư mục apps."

    apps = [d for d in os.listdir(apps_path) if os.path.isdir(os.path.join(apps_path, d)) and not d.startswith('__')]
    
    # 1. Update Apps Section
    manifest.append("## 1. Hệ thống Modules (Apps)")
    for app in apps:
        desc = APP_DESC.get(app, "Chưa có mô tả nghiệp vụ")
        manifest.append(f"- **{app}**: {desc}")
    
    # 2. Detailed Structure Section
    manifest.append("\n## 2. Bản đồ Class & Luồng (Tự động hóa)")
    for app in apps:
        app_path = os.path.join(apps_path, app)
        manifest.append(f"\n### App: {app}")
        
        # Đọc README.md nếu có
        readme_path = os.path.join(app_path, 'README.md')
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                manifest.append(f"#### Mô tả chi tiết:\n{f.read().strip()}\n")

        # Đọc các file code quan trọng
        for file in ['models.py', 'views.py', 'services.py']:
            file_path = os.path.join(app_path, file)
            if os.path.exists(file_path):
                manifest.append(f"#### File: `{file}`")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Thêm phần trích xuất file-level docstring (Luồng AI)
                    tree = ast.parse(content)
                    file_doc = ast.get_docstring(tree)
                    if file_doc:
                        manifest.append(f"*{file_doc.splitlines()[0]}*")

                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            doc = ast.get_docstring(node) or "Chưa có mô tả"
                            manifest.append(f"- **Class {node.name}**: {doc.splitlines()[0]}")
    return "\n".join(manifest)

if __name__ == "__main__":
    # Đảm bảo đường dẫn root là thư mục dự án
    content = get_manifest_content(os.getcwd())
    with open('PROJECT_MANIFEST.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Đã tạo xong PROJECT_MANIFEST.md với cấu trúc chi tiết.")