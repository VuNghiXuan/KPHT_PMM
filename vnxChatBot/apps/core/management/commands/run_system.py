import os
import subprocess
import sys
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Khởi động đồng thời Uvicorn (ASGI) và Celery Worker cho môi trường Local"

    def handle(self, *args, **options):
        # Ép buộc Python sử dụng UTF-8 trên Windows để tránh lỗi mã hóa
        os.environ["PYTHONUTF8"] = "1"
        
        self.stdout.write(self.style.SUCCESS("🚀 [VnxChatBot] Đang khởi động hệ thống tích hợp..."))

        # Khởi chạy Uvicorn và Celery dưới dạng các tiến trình con song song
        uvicorn_process = None
        celery_process = None

        try:
            # 1. Chạy Uvicorn ASGI Server
            uvicorn_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "config.asgi:application", 
                "--host", "0.0.0.0", 
                "--port", "8000", 
                "--reload"
            ])

            # 2. Chạy Celery Worker cho queue xử lý tài liệu P1
            celery_process = subprocess.Popen([
                sys.executable, "-m", "celery", 
                "-A", "config", 
                "worker", 
                "-Q", "documents_p1_processing", 
                "--pool=solo", 
                "-l", "info"
            ])

            # Giữ tiến trình chạy liên tục cho đến khi người dùng bấm Ctrl+C
            uvicorn_process.wait()
            celery_process.wait()

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n🛑 Đang dừng hệ thống và dọn dẹp tiến trình..."))
            if uvicorn_process:
                uvicorn_process.terminate()
            if celery_process:
                celery_process.terminate()
            self.stdout.write(self.style.SUCCESS("✅ Hệ thống đã dừng hoàn toàn an toàn."))