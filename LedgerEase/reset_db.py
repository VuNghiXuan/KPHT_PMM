import os
import shutil

def reset_project():
    # 1. Xóa file database
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("Đã xóa db.sqlite3")

    # 2. Xóa file migration
    apps_dir = 'apps'
    for root, dirs, files in os.walk(apps_dir):
        if 'migrations' in dirs:
            mig_path = os.path.join(root, 'migrations')
            for file in os.listdir(mig_path):
                if file != '__init__.py':
                    file_path = os.path.join(mig_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Đã xóa: {file_path}")

if __name__ == "__main__":
    reset_project()
    print("Hoàn tất dọn dẹp. Hãy chạy 'python manage.py makemigrations' để bắt đầu lại.")