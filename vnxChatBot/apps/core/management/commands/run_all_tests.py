# -*- coding: utf-8 -*-
"""
File: apps/core/management/commands/run_all_tests.py
Mục đích: Tự động khởi chạy một cửa sổ Terminal mới và thực thi toàn bộ
chuỗi kiểm thử (Automated Test Suite) theo đúng thứ tự tầng kiến trúc VnxChatBot.
"""

import os
import sys
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings



class Command(BaseCommand):
    help = "Bật Terminal mới và chạy toàn bộ quy trình Test theo đúng thứ tự tầng kiến trúc."

    def handle(self, *args, **options):
        # 1. Xác định thư mục gốc của dự án (nơi chứa file manage.py)
        base_dir = settings.BASE_DIR

        # 2. Định nghĩa danh sách các bài test chuẩn theo thứ tự phụ thuộc (Tầng 1 -> Tầng 4)
        test_sequence = [
            # Tầng 1: Core Platform & User Profile
            "apps.core.tests",
            
            # Tầng 2 & 3: Group Chat & AI Configuration & Conflict Resolution
            "apps.group_chat.tests.test_group_chat",
            "apps.group_chat.tests.test_ai_config",
            "apps.group_chat.tests.test_conflict_resolution_api",  # 👈 Bổ sung bài test Conflict Resolution vừa hoàn thành
            "apps.group_chat.tests.tests_knowledge_views",
            "apps.group_chat.tests.test_knowledge_search",
            
            "apps.group_chat.tests.test_tasks",
            "apps.group_chat.tests.test_document_pipeline",
            "apps.group_chat.tests.test_conflict_chapter_list_api",
            "apps.group_chat.tests.test_ai_rewrite_api",

            # Tầng 3: AI Assistant & WebSockets Realtime
            "apps.ai_assistant.tests",
            "apps.group_chat.tests.tests_chat_consumer",
            "apps.group_chat.tests.tests_WebSocketRAGAndFeedback", #
            
            # Tầng 4: Subscriptions & Integration Flow
            "apps.subscriptions.tests",
            "apps.arch_manager.tests",
        ]

        # 3. Tạo chuỗi lệnh Batch thực thi trên Terminal mới
        batch_commands = [f'cd /d "{base_dir}"']

        # Kích hoạt môi trường ảo nếu tồn tại thư mục env
        env_activate = os.path.join(base_dir, "env", "Scripts", "activate.bat")
        if os.path.exists(env_activate):
            batch_commands.append(f'call "{env_activate}"')

        batch_commands.append("echo ========================================================")
        batch_commands.append("echo   VNXCHATBOT - HOAN THANH KHOI TAO HE THONG KIEM THU")
        batch_commands.append("echo ========================================================")

        # Thêm từng lệnh test vào chuỗi (kèm theo cờ --keepdb)
        for test_target in test_sequence:
            batch_commands.append("echo.")
            batch_commands.append(f"echo [RUNNING TEST]: python manage.py test {test_target} --keepdb")
            batch_commands.append(f"python manage.py test {test_target} --keepdb")

        # Sau khi chạy hết các test suite chuẩn, gọi luôn lệnh chẩn đoán hệ thống test_flow nếu có
        batch_commands.append("echo.")
        batch_commands.append("echo [RUNNING DIAGNOSTIC]: python manage.py test_flow")
        batch_commands.append("python manage.py test_flow")

        # Giữ cửa sổ terminal không bị tắt sau khi hoàn thành
        batch_commands.append("echo.")
        batch_commands.append("echo ========================================================")
        batch_commands.append("echo   DA HOAN THANH TOAN BO CHUONG TRINH KIEM THU VA CHAN DOAN!")
        batch_commands.append("echo ========================================================")
        batch_commands.append("pause")

        # Nối các câu lệnh bằng dấu && trong Command Prompt
        full_command_str = " && ".join(batch_commands)

        # 4. Kích hoạt Terminal (cmd.exe) trong cửa sổ độc lập mới bằng subprocess
        try:
            self.stdout.write(self.style.SUCCESS("🚀 Đang bật cửa sổ Terminal mới để chạy chuỗi Test..."))
            subprocess.Popen(
                f'start cmd /k "{full_command_str}"',
                shell=True,
                cwd=base_dir
            )
            self.stdout.write(self.style.SUCCESS("✅ Đã khởi tạo tiến trình test thành công trong Terminal mới!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Không thể bật Terminal mới: {str(e)}"))

# python manage.py run_all_tests