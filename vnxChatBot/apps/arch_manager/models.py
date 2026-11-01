"""
Module: arch_manager.models
Author: Senior Software Engineer & Architecture Lead
Description: Lưu trữ bản đồ kiến trúc hệ thống, đồng thời tích hợp cơ chế nội soi 
             (Introspection) để tự động quét models.py và sinh sơ đồ ERD thời gian thực.
"""

import inspect
from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _


class SystemBlueprint(models.Model):
    """
    Class: SystemBlueprint
    Description: 
        Đại diện cho phiên bản kiến trúc hệ thống. Hỗ trợ tự động trích xuất cấu trúc 
        từ các app trong dự án VnxChatBot để làm tài liệu sống (Living Documentation).
    """
    
    version = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Phiên bản kiến trúc"),
        help_text=_("Ví dụ: v1.0.0, v1.1.0-beta")
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name=_("Tiêu đề bản thiết kế"),
        help_text=_("Tên mô tả ngắn gọn cho bản cập nhật kiến trúc này.")
    )
    
    code_flow_mermaid = models.TextField(
        blank=True,
        verbose_name=_("Sơ đồ luồng mã nguồn (Code Flow)"),
        help_text=_("Mã nguồn Mermaid minh họa luồng dữ liệu: User -> FileProcessor -> VectorStore -> LLM.")
    )
    
    erd_mermaid = models.TextField(
        blank=True,
        verbose_name=_("Sơ đồ thực thể ERD (Tự động quét từ Models)"),
        help_text=_("Mã nguồn ERD sinh tự động hoặc tùy chỉnh thủ công gắn liền với ranh giới group_id.")
    )
    
    state_machine_mermaid = models.TextField(
        blank=True,
        verbose_name=_("Sơ đồ trạng thái (State Machine)"),
        help_text=_("Mô tả vòng đời tri thức KnowledgeUnit: pending -> approved/rolled_back.")
    )
    
    component_mermaid = models.TextField(
        blank=True,
        verbose_name=_("Sơ đồ kiến trúc Module (Component Diagram)"),
        help_text=_("Mô tả sự tương tác giữa các app cốt lõi trong hệ thống Modular Monolith.")
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_("Mô tả chi tiết thay đổi"),
        help_text=_("Giải thích lý do (Why) đằng sau các quyết định kiến trúc trong phiên bản này.")
    )
    
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Đang áp dụng"),
        help_text=_("Đánh dấu phiên bản kiến trúc hiện hành đang chạy trên hệ thống.")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Thời gian tạo")
    )

    class Meta:
        verbose_name = _("Bản thiết kế hệ thống")
        verbose_name_plural = _("Các bản thiết kế hệ thống")
        ordering = ['-created_at']

    def __str__(self):
        status = " [ACTIVE]" if self.is_active else ""
        return f"Blueprint {self.version}: {self.title}{status}"

    @classmethod
    def generate_dynamic_erd(cls) -> str:
        """Tự động nội soi 100%: Quét toàn bộ apps, models và thể hiện rõ mối quan hệ 1-n (Multiplicity)."""
        from django.apps import apps
        from django.db import models
        
        mermaid_lines = ["classDiagram"]
        processed_models = set()
        relationship_lines = set()

        excluded_apps = {'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles'}
        
        for app_config in apps.get_app_configs():
            app_label = app_config.label
            if app_label in excluded_apps:
                continue
                
            app_models = [m for m in app_config.get_models() if m.__name__ not in processed_models]
            if not app_models:
                continue

            mermaid_lines.append(f"    namespace {app_label} {{")
            
            for model in app_models:
                model_name = model.__name__
                processed_models.add(model_name)
                
                mermaid_lines.append(f"        class {model_name} {{")
                
                for field in model._meta.get_fields():
                    if field.concrete and not field.many_to_many and not field.one_to_one:
                        field_name = field.name
                        if field.primary_key:
                            mermaid_lines.append(f"            string {field_name} PK")
                        elif isinstance(field, models.ForeignKey):
                            mermaid_lines.append(f"            string {field_name}_id FK")
                            
                            related_model_name = field.related_model.__name__
                            # Bổ sung ký hiệu multiplicity: 1 bản ghi cha có thể chứa nhiều bản ghi con (0..*)
                            rel_line = f'    {related_model_name} "1" --> "0..*" {model_name} : "{field.name}"'
                            relationship_lines.add(rel_line)
                        else:
                            if field_name in ['name', 'title', 'status', 'role', 'is_ai', 'created_at', 'plan_type', 'username']:
                                mermaid_lines.append(f"            string {field_name}")
                
                mermaid_lines.append("        }")
            
            mermaid_lines.append("    }")

        mermaid_lines.extend(list(relationship_lines))

        return "\n".join(mermaid_lines)