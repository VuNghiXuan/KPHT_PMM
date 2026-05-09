import os
import shutil
from pathlib import Path

def reset_project():
    # Thư mục gốc của dự án
    base_dir = Path(__file__).resolve().parent
    
    # 1. Các thư mục cần bỏ qua tuyệt đối
    ignored_dirs = ['venv', '.git', '.vscode', 'env']
    
    print(f"🚀 Đang bắt đầu làm sạch dự án tại: {base_dir}")
    print(f"⚠️  Đã loại trừ không đụng đến: {ignored_dirs}")
    print("-" * 50)

    for path in base_dir.rglob('*'):
        # Kiểm tra nếu đường dẫn nằm trong các thư mục bị bỏ qua
        if any(ignored in path.parts for ignored in ignored_dirs):
            continue

        # 2. Xóa các file Database (db.sqlite3)
        if path.name == 'db.sqlite3':
            try:
                path.unlink()
                print(f"✅ Đã xóa Database: {path}")
            except Exception as e:
                print(f"❌ Lỗi khi xóa DB: {e}")

        # 3. Xóa các file Migrations (giữ lại __init__.py)
        if 'migrations' in path.parts and path.suffix == '.py' and path.name != '__init__.py':
            try:
                path.unlink()
                print(f"✅ Đã xóa Migration: {path.relative_to(base_dir)}")
            except Exception as e:
                print(f"❌ Lỗi xóa file migration: {e}")

        # 4. Xóa các thư mục __pycache__
        if path.name == '__pycache__' and path.is_dir():
            try:
                shutil.rmtree(path)
                print(f"✅ Đã dọn dẹp cache: {path.relative_to(base_dir)}")
            except Exception as e:
                print(f"❌ Lỗi xóa cache: {e}")

    print("-" * 50)
    print("🎉 Hoàn tất! Dự án đã sạch sẽ.")
    print("👉 Bây giờ anh có thể chạy: python manage.py makemigrations && python manage.py migrate")

if __name__ == "__main__":
    reset_project()