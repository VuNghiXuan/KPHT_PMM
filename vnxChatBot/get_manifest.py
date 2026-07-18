import os
import ast

# Danh mục app mới của VnxChatBot
APP_DESC = {
    "group_chat": "Quản lý Nhóm, Thành viên, Tài liệu và Feedback.",
    "ai_assistant": "Bộ não AI, RAG Engine, Vector Store và LLM Service.",
    "subscriptions": "Quản lý gói dịch vụ và giới hạn thành viên theo Group.",
    "arch_manager": "Kho lưu trữ kiến trúc, sơ đồ và luồng hệ thống."
}

def get_vnx_manifest(root_dir):
    manifest = ["# VnxChatBot Project Manifest\n", f"> *Cập nhật: {os.popen('date /t').read().strip()}*\n"]
    apps_path = os.path.join(root_dir, 'apps')
    
    if not os.path.exists(apps_path):
        return "Lỗi: Không tìm thấy thư mục apps."

    # Chỉ quét các app trong VnxChatBot
    apps = [d for d in os.listdir(apps_path) if d in APP_DESC]
    
    manifest.append("## 1. Hệ thống Modules (Apps)")
    for app in apps:
        manifest.append(f"- **{app}**: {APP_DESC.get(app)}")
    
    manifest.append("\n## 2. Bản đồ Class & Luồng (Tự động hóa)")
    for app in apps:
        app_path = os.path.join(apps_path, app)
        manifest.append(f"\n### App: {app}")
        
        # Chỉ quét các file cốt lõi
        for file in ['models.py', 'services.py', 'signals.py']:
            file_path = os.path.join(app_path, file)
            if os.path.exists(file_path):
                manifest.append(f"#### File: `{file}`")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    try:
                        tree = ast.parse(content)
                        # Lấy Docstring file
                        if ast.get_docstring(tree):
                            manifest.append(f"*{ast.get_docstring(tree).splitlines()[0]}*")
                        # Lấy Class
                        for node in tree.body:
                            if isinstance(node, ast.ClassDef):
                                doc = ast.get_docstring(node) or "Chưa có mô tả"
                                manifest.append(f"- **Class {node.name}**: {doc.splitlines()[0]}")
                    except SyntaxError:
                        manifest.append("*Lỗi cú pháp file*")
    return "\n".join(manifest)

if __name__ == "__main__":
    with open('VNX_PROJECT_MANIFEST.md', 'w', encoding='utf-8') as f:
        f.write(get_vnx_manifest(os.getcwd()))
    print("Đã tạo xong VNX_PROJECT_MANIFEST.md chuẩn VnxChatBot.")