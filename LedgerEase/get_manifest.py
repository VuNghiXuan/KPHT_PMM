import os
import ast

def get_manifest_content(root_dir):
    manifest = ["# LedgerEase Project Manifest\n"]
    
    # Duyệt qua các apps
    apps_path = os.path.join(root_dir, 'apps')
    if not os.path.exists(apps_path):
        return "Không tìm thấy thư mục apps"

    apps = [d for d in os.listdir(apps_path) if os.path.isdir(os.path.join(apps_path, d)) and not d.startswith('__')]
    
    # 1. Apps Section
    manifest.append("## 1. Hệ thống Modules (Apps)")
    for app in apps:
        manifest.append(f"- **{app}**: [Điền mô tả nghiệp vụ tại đây]")
    
    # 2. Detailed Structure Section
    manifest.append("\n## 2. Bản đồ Class & Phương thức")
    
    for app in apps:
        app_path = os.path.join(apps_path, app)
        manifest.append(f"\n### App: {app}")
        
        for file in os.listdir(app_path):
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(app_path, file)
                manifest.append(f"#### File: `{file}`")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in tree.body:
                            if isinstance(node, ast.ClassDef):
                                doc = ast.get_docstring(node) or "Chưa có mô tả"
                                manifest.append(f"- **Class {node.name}**: {doc}")
                                for item in node.body:
                                    if isinstance(item, ast.FunctionDef):
                                        manifest.append(f"  - *Method*: `{item.name}()`")
                    except Exception:
                        continue
    return "\n".join(manifest)

# Lưu lại
if __name__ == "__main__":
    content = get_manifest_content(os.getcwd())
    with open('PROJECT_MANIFEST.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Đã tạo xong PROJECT_MANIFEST.md với cấu trúc chi tiết.")