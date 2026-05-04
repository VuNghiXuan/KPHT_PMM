import os
import glob

def clean_migrations():
    # Tìm tất cả các thư mục migrations trong project
    migration_dirs = glob.glob("**/migrations", recursive=True)
    
    for d in migration_dirs:
        # Tìm các file .py trong thư mục migrations
        files = glob.glob(os.path.join(d, "*.py"))
        for f in files:
            # Không xóa file __init__.py
            if not f.endswith("__init__.py"):
                os.remove(f)
                print(f"✅ Đã xóa: {f}")

if __name__ == "__main__":
    clean_migrations()