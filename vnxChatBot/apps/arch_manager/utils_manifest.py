"""
Mục đích: Tự động nội soi toàn diện cấu trúc dự án VnxChatBot (App, Thư mục, File, Class, Method), 
          xuất ra tệp VNX_PROJECT_MANIFEST.md phản ánh chính xác trạng thái Living Architecture.
Tác giả: Kiến trúc sư VnxChatBot
"""
import os
import ast
from datetime import datetime

# Danh mục app chuẩn của VnxChatBot theo mô hình Modular Monolith
APP_DESC = {
    "group_chat": "Quản lý Nhóm, Thành viên, Tài liệu, Vòng đời tri thức và Feedback.",
    "ai_assistant": "Bộ não AI, RAG Engine, Vector Store và LLM Service (AIFactory).",
    "subscriptions": "Quản lý gói dịch vụ và giới hạn thành viên theo ChatGroup.",
    "arch_manager": "Kho lưu trữ kiến trúc, sơ đồ tự động nội soi và KnowledgeUnit.",
    "core": "Nền tảng hệ thống (User, Profile, Auth cơ bản)."
}

def scan_directory_recursive(dir_path, prefix="  "):
    """
    Quét đệ quy các thư mục và tệp tin bên trong một app để hiển thị toàn bộ cây cấu trúc file/folder.
    """
    tree_lines = []
    try:
        items = sorted(os.listdir(dir_path))
    except PermissionError:
        return []

    # Lọc bỏ các tệp tin hệ thống không cần thiết
    ignore_items = {'__pycache__', '.pyc', '.DS_Store', 'migrations'}

    for index, item in enumerate(items):
        if item in ignore_items:
            continue
        
        path = os.path.join(dir_path, item)
        is_last = (index == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        if os.path.isdir(path):
            tree_lines.append(f"{prefix}{connector}📁 **{item}/**")
            extension_prefix = prefix + ("    " if is_last else "│   ")
            tree_lines.extend(scan_directory_recursive(path, extension_prefix))
        else:
            tree_lines.append(f"{prefix}{connector}📄 `{item}`")
            
    return tree_lines

def get_vnx_manifest(root_dir):
    """
    Quét toàn bộ thư mục apps, lập bản đồ cây thư mục chi tiết kết hợp phân tích cây cú pháp AST.
    """
    current_date = datetime.now().strftime("%d/%b/%y")
    manifest = [
        "# VnxChatBot Project Manifest\n", 
        f"> *Cập nhật tự động: {current_date}*\n",
        "> *Tài liệu này phản ánh chính xác cấu trúc thư mục, tệp tin, Class và Hàm thực tế của mã nguồn (Living Architecture).*\n"
    ]
    
    apps_path = os.path.join(root_dir, 'apps')
    if not os.path.exists(apps_path):
        return "Lỗi: Không tìm thấy thư mục apps trong thư mục hiện tại."

    # Lọc các app thuộc hệ thống VnxChatBot
    active_apps = [d for d in os.listdir(apps_path) if d in APP_DESC and os.path.isdir(os.path.join(apps_path, d))]
    
    manifest.append("## 1. Hệ thống Modules (Apps)")
    for app in active_apps:
        manifest.append(f"- **{app}**: {APP_DESC.get(app)}")
    
    manifest.append("\n## 2. Cây Cấu trúc Thư mục & Chi tiết Class/Hàm (Introspection)")
    
    for app in active_apps:
        app_path = os.path.join(apps_path, app)
        manifest.append(f"\n### App: `{app}`")
        manifest.append(f"> *Mô tả:* {APP_DESC.get(app)}")
        
        # 1. Hiển thị cây thư mục và tệp tin thực tế trong app
        manifest.append("\n#### 📂 Cấu trúc thư mục & tệp tin:")
        dir_tree = scan_directory_recursive(app_path)
        if dir_tree:
            manifest.extend(dir_tree)
        else:
            manifest.append("  - *(Thư mục trống)*")
            
        # 2. Quét sâu nội dung mã nguồn qua AST cho các file Python cốt lõi
        manifest.append("\n#### 🔍 Phân tích chi tiết mã nguồn (AST):")
        
        # Liệt kê tất cả các file .py có trong app để quét tự động thay vì chỉ định cứng vài file
        py_files = [f for f in os.listdir(app_path) if f.endswith('.py')]
        # Sắp xếp ưu tiên các file quan trọng lên trước
        priority_order = ['models.py', 'services.py', 'signals.py', 'views.py', 'apps.py', 'admin.py', 'urls.py']
        py_files = sorted(py_files, key=lambda x: priority_order.index(x) if x in priority_order else 99)

        for file in py_files:
            file_path = os.path.join(app_path, file)
            manifest.append(f"- **File: `{file}`**")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Lấy Docstring cấp độ File
                file_doc = ast.get_docstring(tree)
                if file_doc:
                    first_line = file_doc.splitlines()[0]
                    manifest.append(f"  > *Mô tả:* {first_line}")
                
                has_content = False
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        has_content = True
                        class_doc = ast.get_docstring(node) or "Chưa có mô tả Class"
                        class_summary = class_doc.splitlines()[0]
                        manifest.append(f"  - **Class `{node.name}`**: {class_summary}")
                        
                        # Quét các phương thức (Methods) bên trong Class
                        for sub_node in node.body:
                            if isinstance(sub_node, ast.FunctionDef):
                                method_doc = ast.get_docstring(sub_node) or ""
                                method_summary = method_doc.splitlines()[0] if method_doc else "Hàm xử lý nội bộ"
                                manifest.append(f"    - *Method `{sub_node.name}()`*: {method_summary}")
                                
                    elif isinstance(node, ast.FunctionDef):
                        has_content = True
                        func_doc = ast.get_docstring(node) or "Hàm chức năng"
                        func_summary = func_doc.splitlines()[0]
                        manifest.append(f"  - **Function `{node.name}()`**: {func_summary}")
                        
                if not has_content:
                    manifest.append("  - *(File trống hoặc không chứa Class/Function)*")
                    
            except SyntaxError:
                manifest.append("  - *Lỗi cú pháp (SyntaxError) trong file này.*")
                
    return "\n".join(manifest)

if __name__ == "__main__":
    root = os.getcwd()
    manifest_content = get_vnx_manifest(root)
    output_file = 'VNX_PROJECT_MANIFEST.md'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
        
    print(f"🚀 Đã tự động quét toàn bộ thư mục, tệp, class, hàm và cập nhật thành công tệp: {output_file}")