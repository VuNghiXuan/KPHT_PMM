from django.db import models
import os
import ast
from django.conf import settings

class DataType(models.Model):
    """
    Dữ liệu động: AI tự đi lấy và tự tạo ra các loại nghiệp vụ mới.
    Ví dụ: Công thức, Thuật ngữ, Quy trình, hay nhãn mới AI tự phát hiện.
    """
    code = models.CharField(max_length=100, unique=True, verbose_name="Mã định danh")
    name = models.CharField(max_length=255, verbose_name="Tên hiển thị")
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả loại tri thức")
    is_ai_generated = models.BooleanField(default=False, verbose_name="Do AI tự tạo")
    confidence_score = models.FloatField(default=1.0, verbose_name="Độ tin cậy của AI")

    class Meta:
        verbose_name = "Loại tri thức"
        verbose_name_plural = "Các loại tri thức (Dynamic)"

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProjectStructure(models.Model):
    """
    Bản đồ cấu trúc mã nguồn: Tự động đồng bộ với file vật lý.
    """
    OBJ_TYPES = [('FILE', 'File'), ('CLASS', 'Class'), ('FUNC', 'Function')]
    
    path = models.CharField(max_length=500, unique=True, verbose_name="Đường dẫn định danh")
    name = models.CharField(max_length=255, verbose_name="Tên đối tượng")
    obj_type = models.CharField(max_length=10, choices=OBJ_TYPES, verbose_name="Phân loại")
    docstring = models.TextField(null=True, blank=True, verbose_name="Ghi chú trong code")
    ai_description = models.TextField(null=True, blank=True, verbose_name="AI tóm tắt chức năng")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        related_name='children',
        verbose_name="Cấp cha"
    )
    # Thêm trường để lưu thứ tự hiển thị
    level = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, verbose_name="Còn tồn tại")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cấu trúc mã nguồn"
        verbose_name_plural = "Bản đồ cấu trúc hệ thống"

    def __str__(self):
        return f"{self.obj_type}: {self.name}"

    @classmethod
    def sync_project_structure(cls):       
        base_path = settings.BASE_DIR 
        exclude_dirs = {'.git', 'env', 'venv', '__pycache__', 'migrations', 'static', 'media'}
        cls.objects.all().update(is_active=False)

        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    relpath = os.path.relpath(full_path, base_path)

                    # 1. Lưu FILE (Gốc)
                    file_obj, _ = cls.objects.update_or_create(
                        path=relpath,
                        defaults={'name': file, 'obj_type': 'FILE', 'is_active': True, 'level': 0}
                    )
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            tree = ast.parse(f.read())
                            
                        for item in tree.body:
                            # 2. Lưu CLASS (Con của FILE)
                            if isinstance(item, ast.ClassDef):
                                class_obj, _ = cls.objects.update_or_create(
                                    path=f"{relpath}::{item.name}",
                                    defaults={
                                        'name': item.name, 'obj_type': 'CLASS', 'parent': file_obj,
                                        'docstring': ast.get_docstring(item) or "", 'is_active': True, 'level': 1
                                    }
                                )
                                # 3. Lưu FUNC trong CLASS (Cháu của FILE)
                                for sub in item.body:
                                    if isinstance(sub, ast.FunctionDef):
                                        cls.objects.update_or_create(
                                            path=f"{relpath}::{item.name}.{sub.name}",
                                            defaults={
                                                'name': sub.name, 'obj_type': 'FUNC', 'parent': class_obj,
                                                'docstring': ast.get_docstring(sub) or "", 'is_active': True, 'level': 2
                                            }
                                        )

                            # 4. Lưu FUNC độc lập (Con của FILE)
                            elif isinstance(item, ast.FunctionDef):
                                cls.objects.update_or_create(
                                    path=f"{relpath}::{item.name}",
                                    defaults={
                                        'name': item.name, 'obj_type': 'FUNC', 'parent': file_obj,
                                        'docstring': ast.get_docstring(item) or "", 'is_active': True, 'level': 1
                                    }
                                )
                    except Exception as e:
                        print(f"Lỗi soi file {file}: {e}")

        # 3. Dọn dẹp: Những gì vẫn is_active=False nghĩa là file/hàm đó đã bị anh xóa thực tế
        # cls.objects.filter(is_active=False).delete() # Tùy anh muốn xóa hay chỉ ẩn

        print(f"--- Đã vẽ xong bản đồ cấu trúc hệ thống cho dự án: {base_path} ---")

class IntentStore(models.Model):
    """
    Bộ não Router: Lưu câu chát của anh Vũ để AI học tăng cường.
    """
    user_query = models.TextField(verbose_name="Câu hỏi người dùng")
    detected_intent = models.CharField(max_length=255, verbose_name="Ý định đoán được")
    response_logic = models.JSONField(verbose_name="Logic phản hồi") # Lưu vết các bước AI đã làm
    is_correct = models.BooleanField(null=True, blank=True, verbose_name="Đánh giá từ anh Vũ")
    feedback_note = models.TextField(null=True, blank=True, verbose_name="Ghi chú chỉnh sửa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ý định người dùng"
        verbose_name_plural = "Huấn luyện Router (AI Learning)"


class KnowledgeExchange(models.Model):
    """
    Cơ chế Import/Export linh động.
    """
    file_name = models.CharField(max_length=255)
    action_type = models.CharField(max_length=50, verbose_name="Hành động (Import/Export)")
    data_type = models.ForeignKey(DataType, on_delete=models.SET_NULL, null=True, verbose_name="Loại dữ liệu")
    status = models.CharField(max_length=50, default="PENDING")
    summary = models.TextField(null=True, blank=True, verbose_name="Báo cáo kết quả")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lịch sử trao đổi"
        verbose_name_plural = "Lịch sử Import/Export Tri thức"

# system_monitor/models.py

# class IntentMapping(models.Model):
#     """
#     Bảng phân công: Quyết định Intent nào thì dùng Hàm nào và Dữ liệu nào.
#     """
#     intent_name = models.CharField(
#         max_length=100, 
#         unique=True, 
#         verbose_name="Mã ý định (Ví dụ: TRAO_DOI_VANG)"
#     )
    
#     # Kết nối tới "Cái máy tính" (Hàm xử lý trong code)
#     target_function = models.ForeignKey(
#         'ProjectStructure', 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True,
#         limit_choices_to={'obj_type': 'FUNC'}, # Chỉ cho chọn hàm, không chọn file/class
#         verbose_name="Hàm xử lý logic"
#     )
    
#     # Kết nối tới "Cái hồn" (Dữ liệu/Nghiệp vụ nạp từ Excel)
#     # Lưu ý: 'ai_knowledge.DataType' là cách gọi model từ app khác
#     knowledge_source = models.ForeignKey(
#         'ai_knowledge.DataType', 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True,
#         verbose_name="Nguồn tri thức/Nghiệp vụ"
#     )

#     is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")

#     class Meta:
#         verbose_name = "Cấu hình điều hướng"
#         verbose_name_plural = "Bảng điều hướng Intent (Router Mapping)"

#     def __str__(self):
#         return f"{self.intent_name} -> {self.target_function.name if self.target_function else 'N/A'}"