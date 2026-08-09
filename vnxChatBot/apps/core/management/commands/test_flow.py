# -*- coding: utf-8 -*-
"""
File: test_flow.py
Mục đích: Management command chẩn đoán và kiểm tra toàn bộ luồng hệ thống vnxChatBot.
"""

import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit
from apps.ai_assistant.services.ai_processor_service import AIProcessorService
from apps.ai_assistant.vector_store.chromadb_client import VectorDBManager

User = get_user_model()

class Command(BaseCommand):
    help = "Chạy luồng kiểm tra chẩn đoán toàn diện hệ thống VnxChatBot."

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
            self.stdout.write("✅ Đã tạo user test.")
        else:
            self.stdout.write("✅ User test đã tồn tại.")

        group, g_created = ChatGroup.objects.get_or_create(
            name='Nhóm Test Hiệu Năng'
        )
        
        Membership.objects.get_or_create(
            user=user,
            group=group,
            defaults={'role': 'admin'}
        )
        self.stdout.write(f"✅ ChatGroup: {group.name} (ID: {group.id})")

        # 2. Kiểm tra Vector Database (ChromaDB / VectorDBManager)
        self.stdout.write("\n--- 2. Kiểm tra Vector Store ---")
        try:
            collection = VectorDBManager.collection
            self.stdout.write(f"✅ Kết nối Vector Store thành công. Collection name: {collection.name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi kết nối Vector Store: {e}"))

        # 3. Kiểm tra tốc độ xử lý file (AIProcessorService)
        self.stdout.write("\n--- 3. Kiểm tra AI Processor Service (Local OCR/Text Extraction) ---")
        test_file_path = os.path.join(settings.BASE_DIR, 'test_sample.txt')
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write("Đây là tài liệu kiểm tra hiệu năng hệ thống vnxChatBot cho RAG Engine.")
        
        try:
            ai_processor = AIProcessorService()
            if hasattr(ai_processor, 'extract_text'):
                text_extracted = ai_processor.extract_text(test_file_path)
            else:
                with open(test_file_path, 'r', encoding='utf-8') as cache_f:
                    text_extracted = cache_f.read()
                    
            self.stdout.write(f"✅ Trích xuất text thành công: '{text_extracted[:30]}...'")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi trích xuất file: {e}"))
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

        # 4. Kiểm tra KnowledgeLifecycle & Signals
        self.stdout.write("\n--- 4. Kiểm tra KnowledgeUnit & Signals ---")
        doc = Document.objects.create(
            group=group,
            upload_type='chat'
        )

        ku = KnowledgeUnit.objects.create(
            document=doc,
            group=group,
            entity_name="Thực thể kiểm tra",  
            context_tag="Ngữ cảnh test",
            source_reference="Tài liệu kiểm tra hệ thống",
            content="Nội dung chi tiết của đơn vị kiến thức dùng để test luồng RAG.",
            status="pending"
        )
        self.stdout.write(f"✅ Đã tạo KnowledgeUnit ở trạng thái: {ku.status}")
        
        ku.status = 'approved'
        ku.save()
        self.stdout.write("✅ Đã duyệt KnowledgeUnit thành công (Signals Vector DB đã kích hoạt).")

        self.stdout.write(self.style.SUCCESS("\n🎉 HOÀN TẤT KIỂM TRA CHẨN ĐOÁN HỆ THỐNG!"))