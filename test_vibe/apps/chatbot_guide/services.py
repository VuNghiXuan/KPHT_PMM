# apps/chatbot_guide/services.py
import logging
from django.apps import apps
from .models import GuideCategory, GuideEntry

logger = logging.getLogger(__name__)

class WikiAutoGenerator:
    @staticmethod
    def generate_system_map_lesson():
        """
        Chiến thuật tự thấu hiểu (Self-Documenting Architecture):
        Tự động quét mã nguồn các app nội bộ, trích xuất cấu trúc Model,
        bóc tách mối quan hệ Khóa ngoại để tự sinh mã đồ họa Mermaid.js chuẩn cấu trúc,
        biên dịch bảng từ điển giải nghĩa các trường dữ liệu và lưu đè trực tiếp vào bài học Wiki.
        """
        # Danh sách các app nội bộ của Kim Phát Hiệp Thành cần đưa vào hệ thống Wiki tự thấu hiểu
        target_apps = ['app_ai_core', 'app_coach', 'app_knowledge', 'app_miner', 'chatbot_guide']
        
        raw_structure = []
        
        # 1. Khởi tạo danh sách chuỗi Mermaid tách biệt
        mermaid_base = [
            "```mermaid",
            "graph TD",
            "    %% Định nghĩa các lớp Style cho sơ đồ uốn lượn trực quan",
            "    classDef appStyle fill:#f8f9fa,stroke:#343a40,stroke-width:2px,stroke-dasharray: 5 5;",
            "    classDef modelStyle fill:#ffffff,stroke:#007bff,stroke-width:1px,border-radius:4px;",
            "    "
        ]
        
        mermaid_subgraphs = []  # Chứa định nghĩa các cụm khối (Subgraph)
        mermaid_relations = []  # Chứa các đường mũi tên liên kết (Phải để ngoài Subgraph mới đúng sơ đồ)

        # 2. Thực hiện càn quét thông tin phản xạ từ Django Apps
        for app_label in target_apps:
            try:
                app_config = apps.get_app_config(app_label)
            except LookupError:
                logger.warning(f"⚠️ App '{app_label}' không tìm thấy trong hệ thống, bỏ qua quét.")
                continue
                
            app_verbose = getattr(app_config, 'verbose_name', app_label)
            app_info = {
                "app_label": app_label,
                "app_name": app_verbose,
                "models": []
            }
            
            # Khai báo mở Subgraph cho riêng App này
            mermaid_subgraphs.append(f"    subgraph SUB_{app_label} [App: {app_verbose}]")
            
            for model in app_config.get_models():
                model_name = model.__name__
                model_verbose = getattr(model._meta, 'verbose_name', model_name)
                
                fields_info = []
                for field in model._meta.get_fields():
                    if not field.is_relation or field.many_to_one:
                        field_name = field.name
                        field_type = field.get_internal_type()
                        field_verbose = str(getattr(field, 'verbose_name', field_name))
                        field_help = str(getattr(field, 'help_text', ''))

                        fields_info.append({
                            "name": field_name,
                            "type": field_type,
                            "verbose": field_verbose,
                            "help_text": field_help
                        })
                        
                        # TRÍCH XUẤT QUAN HỆ KHÓA NGOẠI: Đẩy vào mảng độc lập nằm ngoài subgraph
                        if field.is_relation and field.many_to_one:
                            target_model_name = field.related_model.__name__
                            target_app_label = field.related_model._meta.app_label
                            
                            if target_app_label in target_apps:
                                link_line = f"    {app_label}_{model_name} -->|Khóa ngoại: {field_name}| {target_app_label}_{target_model_name}"
                                if link_line not in mermaid_relations:
                                    mermaid_relations.append(link_line)

                # Thu thập chuỗi tài liệu giải thích (Docstring)
                model_doc = model.__doc__ or ""
                clean_doc = " ".join([line.strip() for line in model_doc.splitlines() if line.strip()])
                if not clean_doc or "SystemArchitectureMap" in model_name or "AIPromptConfig" in model_name:
                    clean_doc = f"Quản lý danh mục dữ liệu nghiệp vụ cho {model_verbose}."

                app_info["models"].append({
                    "class_name": model_name,
                    "model_name": model_verbose,
                    "fields": fields_info,
                    "doc": clean_doc
                })
                
                # Khai báo định danh khối Model nằm TRONG subgraph
                mermaid_subgraphs.append(f"        {app_label}_{model_name}[Model: {model_verbose}]")
                mermaid_subgraphs.append(f"        class {app_label}_{model_name} modelStyle;")
            
            # Đóng Subgraph và ép style đường viền đứt nét cho phân vùng App
            mermaid_subgraphs.append("    end")
            mermaid_subgraphs.append(f"    style SUB_{app_label} appStyle;")
            raw_structure.append(app_info)
            
        # 3. Gộp cấu trúc chuỗi Mermaid theo thứ tự chuẩn: Cấu hình chung -> Khối hộp phân vùng -> Mũi tên liên kết
        full_mermaid_graph = (
            "\n".join(mermaid_base) + "\n" +
            "\n".join(mermaid_subgraphs) + "\n\n" +
            "    %% --- ĐƯỜNG DI CHUYỂN LUỒNG DỮ LIỆU LIÊN KẾT NGOÀI SUBGRAPH ---\n" +
            "\n".join(mermaid_relations) + "\n" +
            "```"
        )

        # 4. Xây dựng tài liệu hướng dẫn giải nghĩa chi tiết cấu trúc (Từ điển DB)
        markdown_body = (
            "## 📖 TỪ ĐIỂN ĐỊNH NGHĨA VÀ CHỨC NĂNG NGHIỆP VỤ\n"
            "Dưới đây là chi tiết các trường dữ liệu được bóc tách tự động từ mã nguồn, "
            "giúp định nghĩa rõ ràng chức năng và kiểu dữ liệu phục vụ cho Chatbot RAG tra cứu:\n\n"
        )
        
        for app in raw_structure:
            markdown_body += f"### 📂 Ứng dụng: {app['app_name']} (`{app['app_label']}`)\n"
            
            for m in app['models']:
                markdown_body += f"#### 🔹 Class Model: {m['model_name']} (`{m['class_name']}`)\n"
                markdown_body += f"- **Mô tả chức năng:** *{m['doc']}*\n"
                markdown_body += "- **Danh mục trường dữ liệu chi tiết:**\n\n"
                
                markdown_body += "| Tên trường (Code) | Ý nghĩa nghiệp vụ | Mô tả chức năng (Help Text) | Định dạng dữ liệu |\n"
                markdown_body += "| :--- | :--- | :--- | :--- |\n"
                
                for f in m['fields']:
                    help_text_display = f['help_text'] if f['help_text'] and f['help_text'].strip() else "---"
                    markdown_body += f"| `{f['name']}` | {f['verbose']} | {help_text_display} | `{f['type']}` |\n"
                
                markdown_body += "\n"

        # 5. Đồng bộ hóa trực tiếp vào cơ sở dữ liệu bài viết Wiki (GuideEntry)
        category, _ = GuideCategory.objects.get_or_create(
            name="Hệ thống Tri thức tự động (Wiki)", 
            defaults={
                "icon": "fa-sitemap", 
                "order": 99.0
            }
        )
        
        entry, created = GuideEntry.objects.get_or_create(
            category=category,
            title="Bản đồ liên kết và Cấu trúc toàn bộ Ứng dụng",
            defaults={
                "order": 1.0,
                "prerequisites": "Dành cho quản trị viên, lập trình viên và ChatBot_HTJ đọc hiểu logic DB.",
                "ai_notes": "Sơ đồ và nội dung từ điển được sinh tự động bằng cơ chế Metadata Reflection.",
                "is_reviewed": True
            }
        )
        
        entry.content = (
            f"# 🗺️ BẢN ĐỒ TOÀN BỘ ỨNG DỤNG & LUỒNG DI CHUYỂN DỮ LIỆU\n\n"
            f"### 📊 SƠ ĐỒ KHỐI LIÊN KẾT KIẾN TRÚC\n"
            f"Sơ đồ dưới đây mô tả cấu trúc quan hệ ràng buộc khóa ngoại thực tế giữa các app và models:\n\n"
            f"{full_mermaid_graph}\n\n"
            f"{markdown_body}"
        )
        entry.is_reviewed = True
        entry.save()
        
        return entry