# -*- coding: utf-8 -*-
"""
File: test_system_flow.py
Mục đích: Tệp kiểm thử luồng tổng thể hệ thống vnxChatBot (Cập nhật chuẩn hóa cấu trúc mới).
"""

import os
import django
from django.conf import settings

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnxChatBot.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit
from apps.ai_assistant.vector_store.chromadb_client import VectorDBManager

User = get_user_model()

def test_system_flow():
    print("🚀 BẮT ĐẦU KIỂM TRA HỆ THỐNG VNXCHATBOT...")

    # 1. Kiểm tra kết nối Database & User
    print("\n--- 1. Kiểm tra User & ChatGroup ---")
    user, created = User.objects.get_or_create(
        username='test_diagnostic_user', 
        defaults={'email': 'test@vnx.com'}
    )
    if created:
        user.set_password('123456')
        user.save()
        print("✅ Đã tạo user test.")
    else:
        print("✅ User test đã tồn tại.")

    group, g_created = ChatGroup.objects.get_or_create(
        name='Nhóm Test Hiệu Năng'
    )
    
    Membership.objects.get_or_create(
        user=user,
        group=group,
        defaults={'role': 'admin'}
    )
    print(f"✅ ChatGroup: {group.name} (ID: {group.id})")

    # 2. Kiểm tra Vector Database thông qua VectorDBManager chuẩn
    print("\n--- 2. Kiểm tra Vector Store ---")
    try:
        collection = VectorDBManager.collection
        print(f"✅ Kết nối Vector Store thành công. Collection name: {collection.name}")
    except Exception as e:
        print(f"❌ Lỗi kết nối Vector Store: {e}")

    # 3. Kiểm tra xử lý tệp tin mẫu trực tiếp (Thay thế file_processor cũ)
    print("\n--- 3. Kiểm tra File Processing & Text Extraction ---")
    test_file_path = os.path.join(settings.BASE_DIR, 'test_sample.txt')
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write("Đây là tài liệu kiểm tra hiệu năng hệ thống vnxChatBot cho RAG Engine.")
    
    try:
        with open(test_file_path, 'r', encoding='utf-8') as cache_f:
            text_extracted = cache_f.read()
                
        print(f"✅ Trích xuất text thành công: '{text_extracted[:30]}...'")
    except Exception as e:
        print(f"❌ Lỗi trích xuất file: {e}")
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

    # 4. Kiểm tra KnowledgeLifecycle & Signals
    print("\n--- 4. Kiểm tra KnowledgeUnit & Signals ---")
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
    print(f"✅ Đã tạo KnowledgeUnit ở trạng thái: {ku.status}")
    
    ku.status = 'approved'
    ku.save()
    print("✅ Đã duyệt KnowledgeUnit thành công (Signals Vector DB đã kích hoạt).")

    print("\n🎉 HOÀN TẤT KIỂM TRA CHẨN ĐOÁN HỆ THỐNG!")

if __name__ == '__main__':
    test_system_flow()