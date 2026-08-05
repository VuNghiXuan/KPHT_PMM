# File: apps/group_chat/views/knowledge_views.py

"""
File: apps/group_chat/views/knowledge_views.py
Mục đích: Quản lý vòng đời tri thức (Knowledge Lifecycle), upload tài liệu và phê duyệt RAG.
Module liên kết: group_chat.models, ai_assistant.engine
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction  # Đảm bảo tính toàn vẹn dữ liệu
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit, Message

from django.contrib.auth import get_user_model

User = get_user_model()
# Khởi tạo logger để theo dõi debug
logger = logging.getLogger(__name__)


@login_required
def upload_document(request, group_id):
    """
    Function: upload_document
    Description: 
        Nhận file tải lên từ giao diện chat, lưu trữ vào thư mục riêng của ChatGroup Tenant, 
        tạo bản ghi Document. Signal post_save sẽ tự động kích hoạt tiến trình trích xuất RAG.
    """
    if request.method == 'POST' and request.FILES.get('file'):
        group = get_object_or_404(ChatGroup, id=group_id)
        uploaded_file = request.FILES['file']
        
        try:
            # và lược bỏ trường 'title' nếu Model Document không khai báo trường này.
            document = Document.objects.create(
                group=group,             # Khớp với field 'group' trong ChatGroup
                file=uploaded_file,
                uploaded_by=request.user
            )
            return JsonResponse({
                'status': 'success', 
                'message': 'Upload file thành công. AI đang tiến hành xử lý tri thức!',
                'document_id': document.id
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file hoặc sai phương thức.'}, status=400)

def knowledge_management(request, group_id):
    """
    View quản lý kho tri thức (Knowledge Base) của nhóm.
    Cho phép Admin nhóm xem danh sách tài liệu và các đơn vị tri thức (KnowledgeUnit) 
    để thực hiện duyệt (approve) hoặc từ chối/rollback.
    """
    # 1. Lấy thông tin nhóm hiện tại (Tenant isolation theo group_id)
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # 2. Sửa lại câu lệnh query để tránh lỗi ValueError: 
    # KnowledgeUnit liên kết với Document, Document mới liên kết với ChatGroup.
    knowledge_units = KnowledgeUnit.objects.filter(document__group=group).select_related('document')
    
    # 3. Lấy danh sách tài liệu đã upload của nhóm
    documents = Document.objects.filter(group=group)

    context = {
        'group': group,
        'knowledge_units': knowledge_units,
        'documents': documents,
    }
    
    return render(request, 'group_chat/knowledge_management.html', context)

@login_required
def knowledge_action_view(request, knowledge_id, action):
    """
    Thực hiện phê duyệt (approve) hoặc rollback (vòng đời tri thức) đối với KnowledgeUnit.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)
        
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id)
    
    if action == 'approve':
        ku.status = 'approved'
        ku.save() 
        return JsonResponse({'status': 'success', 'message': 'Đã duyệt tri thức và đồng bộ vào Vector DB!'})
    elif action == 'rollback':
        ku.status = 'rollback'
        ku.save() 
        return JsonResponse({'status': 'success', 'message': 'Đã rollback tri thức và xóa khỏi Vector DB!'})
        
    return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ!'}, status=400)

@login_required
@require_POST
def promote_knowledge_view(request, message_id):
    """
    Mục đích: Chuyển đổi một tin nhắn hội thoại thành đơn vị tri thức (KnowledgeUnit) 
    hoặc đẩy trạng thái tri thức vào chu trình duyệt (Knowledge Lifecycle).
    
    Module liên kết: apps.group_chat.models (Message, KnowledgeUnit, Document)
    
    Giải thích logic (Why):
    - Đảm bảo gán đầy đủ trường group và document cho KnowledgeUnit, tuân thủ tuyệt đối
      ràng buộc Group-Centric (tenant-based isolation) để tránh lỗi NOT NULL constraint.
    """
    try:
        message = get_object_or_404(Message, id=message_id)
        
        # 1. Kiểm tra quyền thành viên trong nhóm (Tenant Isolation)
        membership = request.user.memberships.filter(group=message.group).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

        # 2. Xác định chính xác User instance để gán vào uploaded_by
        uploader_user = request.user
        if message.sender:
            if hasattr(message.sender, 'user'):  # Trường hợp sender là Membership
                uploader_user = message.sender.user
            elif isinstance(message.sender, User):  # Trường hợp sender là User trực tiếp
                uploader_user = message.sender

        # 3. Tạo hoặc lấy Document tương ứng của nhóm
        document, _ = Document.objects.get_or_create(
            group=message.group,
            defaults={'uploaded_by': uploader_user}
        )
        
        # 4. Tạo hoặc cập nhật đơn vị tri thức KnowledgeUnit gắn chặt với group_id
        knowledge_unit, created = KnowledgeUnit.objects.get_or_create(
            document=document,
            group=message.group,  # 👈 Bổ sung trực tiếp group để thỏa mãn ràng buộc NOT NULL
            content=message.content,
            defaults={
                'status': 'pending'  # Chờ duyệt theo Knowledge Lifecycle
            }
        )
        
        if not created and knowledge_unit.status == 'rollback':
            knowledge_unit.status = 'pending'
            knowledge_unit.content = message.content
            knowledge_unit.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Đã chuyển tin nhắn vào kho tri thức chờ duyệt thành công!',
            'knowledge_id': knowledge_unit.id
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi promote knowledge cho message_id={message_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)
    
@login_required
def rollback_knowledge(request, unit_id):
    """
    Hành động Rollback: Chuyển trạng thái KnowledgeUnit -> Xóa khỏi VectorDB.
    Mục đích: Duy trì sự sạch sẽ của Vector Database theo chuẩn Knowledge Lifecycle.
    """
    unit = get_object_or_404(KnowledgeUnit, id=unit_id)
    group = unit.document.chat_group

    if not Membership.objects.filter(group=group, user=request.user, role='admin').exists():
        return JsonResponse({"error": "Không có quyền thực hiện tác vụ này"}, status=403)

    if request.method == "POST":
        try:
            with transaction.atomic():
                unit.status = 'rollback'
                unit.save() 
            return redirect('group_chat:knowledge_management', group_id=group.id)
        except Exception as e:
            return JsonResponse({"error": f"Lỗi hệ thống: {str(e)}"}, status=500)





