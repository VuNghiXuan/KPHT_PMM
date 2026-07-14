import os
import sys
import django
from django.contrib.auth import get_user_model

# Thiết lập môi trường Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def show_menu():
    print("\n--- NEXUSCHAT PROJECT MANAGER ---")
    print("1. Xóa Database và toàn bộ Migrations (Reset)")
    print("2. Khởi tạo lại hệ thống (Migrate & Create Admin)")
    print("3. Tạo App mới trong thư mục 'apps/'")
    print("4. Thoát")
    return input("\nChọn một mục (1-4): ")

def reset_project():
    if input("!!! CẢNH BÁO: Hành động này sẽ xóa vĩnh viễn dữ liệu. Bạn chắc chắn chứ? (y/n): ") == 'y':
        # 1. Xóa file database
        if os.path.exists('db.sqlite3'):
            os.remove('db.sqlite3')
            print("[!] Đã xóa db.sqlite3")
        
        # 2. Xóa file migration
        for root, dirs, files in os.walk('apps'):
            if 'migrations' in dirs:
                mig_path = os.path.join(root, 'migrations')
                for file in os.listdir(mig_path):
                    file_path = os.path.join(mig_path, file)
                    
                    # CHỈ XÓA NẾU LÀ FILE VÀ KHÔNG PHẢI __init__.py
                    if os.path.isfile(file_path) and file != '__init__.py':
                        os.remove(file_path)
                        print(f"[!] Đã xóa: {file_path}")
                    
                    # NẾU LÀ THƯ MỤC (như __pycache__), ta có thể xóa cả thư mục đó luôn
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                        print(f"[!] Đã xóa thư mục: {file_path}")
                        
        print("[+] Dọn dẹp hoàn tất.")

def init_project():
    print("[*] Đang chạy migrations...")
    # Xóa code cũ và thay bằng quy trình chuẩn hơn
    os.system('python manage.py makemigrations')
    # Thêm check kết quả migration
    result = os.system('python manage.py migrate')
    
    if result != 0:
        print("[!] Migration thất bại! Hãy kiểm tra lỗi trong models.py.")
        return

    print("[*] Đang tạo admin...")
    try:
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@gmail.com', '123456')
            print("[+] Đã tạo admin!")
    except Exception as e:
        print(f"[!] Lỗi khi tạo admin: {e}")
        print("Có thể bảng chưa được tạo, hãy thử chạy 'python manage.py migrate' bằng tay.")

def create_app():
    app_name = input("Nhập tên app muốn tạo: ")
    # 1. Định nghĩa đường dẫn đầy đủ
    app_path = os.path.join('apps', app_name)
    
    # 2. Tạo thư mục đích trước khi chạy lệnh Django
    if not os.path.exists(app_path):
        os.makedirs(app_path)
    
    # 3. Chạy lệnh tạo app của Django trỏ vào thư mục vừa tạo
    # Lệnh này sẽ tạo các file model, views, admin... bên trong apps/tên_app
    os.system(f'python manage.py startapp {app_name} {app_path}')
    
    print(f"\n[+] Đã tạo app tại: {app_path}")
    print(f"[!] LƯU Ý: Hãy thêm 'apps.{app_name}' vào danh sách INSTALLED_APPS trong file 'config/settings.py'")

if __name__ == "__main__":
    while True:
        choice = show_menu()
        if choice == '1':
            reset_project()
        elif choice == '2':
            init_project()
        elif choice == '3':
            create_app()
        elif choice == '4':
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng chọn lại.")