import os
import ast
import traceback
from django.db import models, transaction
from django.conf import settings

class DataType(models.Model):
    """
    Dữ liệu động: Phân loại tri thức (Quy trình, Thuật ngữ, Công thức vàng...)
    """
    code = models.CharField(max_length=100, unique=True, verbose_name="Mã định danh")
    name = models.CharField(max_length=255, verbose_name="Tên hiển thị")
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả")
    is_ai_generated = models.BooleanField(default=False, verbose_name="AI tự tạo")
    confidence_score = models.FloatField(default=1.0)

    class Meta:
        verbose_name = "Loại tri thức"
        verbose_name_plural = "1. Danh mục loại tri thức"

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProjectStructure(models.Model):
    """
    Bản đồ mã nguồn: Đồng bộ tự động cấu trúc Class/Function của hệ thống HTJ.
    """
    OBJ_TYPES = [('FILE', 'File'), ('CLASS', 'Class'), ('FUNC', 'Function')]
    
    path = models.CharField(max_length=500, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    obj_type = models.CharField(max_length=10, choices=OBJ_TYPES)
    docstring = models.TextField(null=True, blank=True)
    ai_description = models.TextField(null=True, blank=True, verbose_name="AI tóm tắt")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    level = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cấu trúc mã nguồn"
        verbose_name_plural = "2. Bản đồ cấu trúc Code"

    def __str__(self):
        return f"[{self.obj_type}] {self.name}"

    @classmethod
    def sync_project_structure(cls):
        """Hàm đồng bộ tối ưu: Tránh treo SQLite khi dự án lớn"""
        base_path = settings.BASE_DIR
        exclude_dirs = {'.git', 'env', 'venv', '__pycache__', 'migrations', 'static', 'media', '.ipynb_checkpoints'}
        
        # Đánh dấu tất cả là inactive trước khi quét
        cls.objects.all().update(is_active=False)
        
        objects_to_save = [] # Dùng list để xử lý batch

        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if not file.endswith('.py'): continue
                
                full_path = os.path.join(root, file)
                relpath = os.path.relpath(full_path, base_path)
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                        tree = ast.parse(source)

                    with transaction.atomic():
                        # 1. Xử lý FILE
                        file_obj, _ = cls.objects.update_or_create(
                            path=relpath,
                            defaults={'name': file, 'obj_type': 'FILE', 'is_active': True, 'level': 0}
                        )

                        for item in tree.body:
                            # 2. Xử lý CLASS
                            if isinstance(item, ast.ClassDef):
                                class_path = f"{relpath}::{item.name}"
                                class_obj, _ = cls.objects.update_or_create(
                                    path=class_path,
                                    defaults={
                                        'name': item.name, 'obj_type': 'CLASS', 'parent': file_obj,
                                        'docstring': ast.get_docstring(item) or "", 'is_active': True, 'level': 1
                                    }
                                )
                                # 3. Xử lý METHODS trong CLASS
                                for sub in item.body:
                                    if isinstance(sub, ast.FunctionDef):
                                        cls.objects.update_or_create(
                                            path=f"{class_path}.{sub.name}",
                                            defaults={
                                                'name': sub.name, 'obj_type': 'FUNC', 'parent': class_obj,
                                                'docstring': ast.get_docstring(sub) or "", 'is_active': True, 'level': 2
                                            }
                                        )

                            # 4. Xử lý FUNC độc lập
                            elif isinstance(item, ast.FunctionDef):
                                cls.objects.update_or_create(
                                    path=f"{relpath}::{item.name}",
                                    defaults={
                                        'name': item.name, 'obj_type': 'FUNC', 'parent': file_obj,
                                        'docstring': ast.get_docstring(item) or "", 'is_active': True, 'level': 1
                                    }
                                )
                except Exception:
                    print(f"Bỏ qua file lỗi: {relpath}")

        return "Sync Complete"


class IntentManagement(models.Model):
    """
    TRUNG TÂM ĐIỀU HƯỚNG: Kết nối Ý định -> Hàm xử lý -> Tri thức nghiệp vụ.
    """
    intent_code = models.CharField("Mã ý định", max_length=100, unique=True)
    display_name = models.CharField("Tên nghiệp vụ", max_length=255)
    
    # Kết nối logic
    handler_func = models.ForeignKey(
        ProjectStructure, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'obj_type': 'FUNC'}, verbose_name="Hàm xử lý (Code)"
    )
    knowledge_type = models.ForeignKey(
        DataType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Loại tri thức (Nghiệp vụ)"
    )

    keywords = models.TextField("Từ khóa nhận diện", help_text="Cách nhau bởi dấu phẩy")
    is_active = models.BooleanField(default=True)
    hit_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Điều hướng & Ý định"
        verbose_name_plural = "3. Trung tâm điều hướng Intent"

    def __str__(self):
        return f"{self.display_name} -> {self.handler_func.name if self.handler_func else 'AI Tự do'}"


class IntentLog(models.Model):
    """
    NHẬT KÝ RLHF: Nơi anh Vũ chấm điểm cho AI.
    """
    intent = models.ForeignKey(IntentManagement, on_delete=models.CASCADE, related_name='logs')
    query_text = models.TextField("Câu hỏi khách")
    ai_response_logic = models.JSONField("Các bước AI thực hiện")
    
    # RLHF (Phần anh Vũ huấn luyện AI)
    is_correct = models.BooleanField("Đúng/Sai", null=True, blank=True)
    feedback_note = models.TextField("Ghi chú chỉnh sửa (VD: Phải bù 60k cho khách)", null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nhật ký huấn luyện"
        verbose_name_plural = "4. Nhật ký & Huấn luyện (RLHF)"