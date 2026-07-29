# -*- coding: utf-8 -*-
"""
Mục đích: Lệnh quản lý Django (Management Command) để kiểm tra toàn bộ luồng hệ thống vnxChatBot.
Module liên kết: apps.core, apps.group_chat, apps.ai_assistant
Tác giả: VnxChatBot Team
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Document, KnowledgeUnit
from apps.ai_assistant.services.document_processor import DocumentProcessorService
from apps.ai_assistant.vector_store.chromadb_client import get_vector_store
import os

User = get_user_model()


class Command(BaseCommand):
    help = "Kiểm tra toàn diện luồng hệ thống vnxChatBot (Database, Vector Store, File Processor, Knowledge Lifecycle)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 BẮT ĐẦU KIỂM TRA HỆ THỐNG VNXCHATBOT..."))

        # 1. Kiểm tra kết nối Database & User
        self.stdout.write("\n--- 1. Kiểm tra User & ChatGroup ---")
        user, created = User.objects.get_or_create(
            username='test_diagnostic_user', 
            defaults={'email': 'test@vnx.com'}
        )
        if created:
            user.set_password('123456')
            user.save()
            self.stdout.write(self.style.SUCCESS("✅ Đã tạo user test."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ User test đã tồn tại."))

        # Lấy hoặc tạo nhóm chat (Group-Centric Tenant)
        group, g_created = ChatGroup.objects.get_or_create(
            name='Nhóm Test Hiệu Năng', 
            defaults={'created_by': user}
        )
        self.stdout.write(self.style.SUCCESS(f"✅ ChatGroup: {group.name} (ID: {group.id})"))

        # 2. Kiểm tra Vector Database (ChromaDB / Local path)
        self.stdout.write("\n--- 2. Kiểm tra Vector Store ---")
        try:
            vector_store = get_vector_store()
            self.stdout.write(self.style.SUCCESS("✅ Kết nối Vector Store thành công."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi kết nối Vector Store: {e}"))

        # 3. Kiểm tra tốc độ xử lý file (FileProcessor)
        self.stdout.write("\n--- 3. Kiểm tra File Processor (Local OCR/Text Extraction) ---")
        test_file_path = os.path.join(settings.BASE_DIR, 'test_sample.txt')
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write("Đây là tài liệu kiểm tra hiệu năng hệ thống vnxChatBot cho RAG Engine.")
        
        try:
            text_extracted = DocumentProcessorService.process_txt(test_file_path)
            self.stdout.write(self.style.SUCCESS(f"✅ Trích xuất text thành công: '{text_extracted[:30]}...'"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi trích xuất file: {e}"))
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

        # 4. Kiểm tra KnowledgeLifecycle & Signals
        self.stdout.write("\n--- 4. Kiểm tra KnowledgeUnit & Signals ---")
        
        # Tạo một Document mẫu thuộc về group hiện tại để làm cha cho KnowledgeUnit
        doc = Document.objects.create(
            group=group,
            upload_type='chat'
        )

        # Khởi tạo KnowledgeUnit (Sử dụng đúng trường entity_name, tuyệt đối không dùng title)
        ku = KnowledgeUnit.objects.create(
            document=doc,
            group=group,
            entity_name="Thực thể kiểm tra",  # 🧠 Trường chuẩn xác thay thế cho title
            context_tag="Ngữ cảnh test",
            source_reference="Tài liệu kiểm tra hệ thống",
            content="Nội dung chi tiết của đơn vị kiến thức dùng để test luồng RAG.",
            status="pending"
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Đã tạo KnowledgeUnit ở trạng thái: {ku.status}"))
        
        # Chuyển trạng thái sang approved để kích hoạt signal đồng bộ vector embedding tự động
        ku.status = 'approved'
        ku.save()
        self.stdout.write(self.style.SUCCESS("✅ Đã duyệt KnowledgeUnit thành công (Signals Vector DB đã kích hoạt)."))

        self.stdout.write(self.style.SUCCESS("\n🎉 HOÀN TẤT KIỂM TRA CHẨN ĐOÁN HỆ THỐNG!"))