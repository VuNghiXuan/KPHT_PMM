"""
Mục đích: Xử lý logic nghiệp vụ cho nhóm chat, quản lý tài liệu và tri thức.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction  # Đảm bảo tính toàn vẹn dữ liệu
from .models import ChatGroup, Membership, Document, KnowledgeUnit
from .services.feedback_service import FeedbackService

# apps/group_chat/views.py
@login_required
def create_group(request):
    """
    Tạo nhóm mới. Mọi nhóm là một Tenant độc lập.
    """
    if request.method == "POST":
        name = request.POST.get("name")
        # Lưu ý: Đảm bảo ChatGroup model đã có field 'name'
        group = ChatGroup.objects.create(name=name)
        
        # Thêm Admin vào Membership
        Membership.objects.create(
            group=group,
            user=request.user,
            role='admin',
            is_ai=False
        )
        return redirect('group_chat:detail', group_id=group.id)
    return render(request, 'group_chat/create.html')

@login_required
def upload_document(request, group_id):
    """
    Upload tài liệu vào nhóm.
    Tự động kích hoạt luồng: Document -> Signals -> FileProcessor -> KnowledgeUnit.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # Kiểm tra quyền: Người dùng phải là thành viên của nhóm
    if not Membership.objects.filter(group=group, user=request.user).exists():
        return JsonResponse({"error": "Bạn không có quyền truy cập nhóm này."}, status=403)

    if request.method == "POST":
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({"error": "Không có file nào được tải lên."}, status=400)
            
        # Tạo Document: Đây là điểm kích hoạt Signal 'post_save' 
        # đã được chúng ta cấu hình để nạp vào VectorDB
        doc = Document.objects.create(
            group=group, 
            file=file,
            uploaded_by=request.user # Giả định bạn có field này trong Document model
        )
        return JsonResponse({
            "message": "Tài liệu đã được tải lên và đang được AI xử lý.", 
            "doc_id": doc.id
        })
    
    return render(request, 'group_chat/upload.html', {'group': group})

@login_required
def knowledge_management(request, group_id):
    """
    Dashboard cho Admin nhóm để duyệt hoặc rollback tri thức.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    membership = get_object_or_404(Membership, group=group, user=request.user)
    
    if membership.role != 'admin':
        return JsonResponse({"error": "Chỉ Admin mới có quyền truy cập"}, status=403)

    # Lấy các đơn vị kiến thức của nhóm
    units = KnowledgeUnit.objects.filter(document__group=group)
    
    return render(request, 'group_chat/knowledge_dashboard.html', {
        'group': group,
        'knowledge_units': units
    })

@login_required
def rollback_knowledge(request, unit_id):
    """
    Hành động Rollback: Chuyển trạng thái KnowledgeUnit -> Xóa khỏi VectorDB.
    Mục đích: Duy trì sự sạch sẽ của Vector Database theo yêu cầu[cite: 1].
    """
    unit = get_object_or_404(KnowledgeUnit, id=unit_id)
    group = unit.document.group

    # Kiểm tra quyền Admin (Tenant Isolation)
    if not Membership.objects.filter(group=group, user=request.user, role='admin').exists():
        return JsonResponse({"error": "Không có quyền thực hiện tác vụ này"}, status=403)

    if request.method == "POST":
        try:
            with transaction.atomic():
                unit.status = 'rollback'
                unit.save() 
                # Signal `handle_knowledge_status_change` sẽ tự động xử lý xóa vector
            return redirect('group_chat:knowledge_management', group_id=group.id)
        except Exception as e:
            return JsonResponse({"error": f"Lỗi hệ thống: {str(e)}"}, status=500)

@login_required
def group_chat_detail(request, group_id):
    """
    Hiển thị giao diện chat chính của nhóm.
    Đảm bảo tính Tenant Isolation: Chỉ thành viên nhóm mới được xem.
    """
    # Lấy nhóm hoặc báo lỗi 404
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # Kiểm tra quyền truy cập (Tenant Isolation)
    if not Membership.objects.filter(group=group, user=request.user).exists():
        return render(request, '403.html', status=403)
    
    context = {
        'group': group,
    }
    return render(request, 'group_chat/detail.html', context)


def knowledge_feedback_view(request, unit_id):
    action = request.POST.get('action') # 'approve' hoặc 'rollback'
    try:
        FeedbackService.handle_feedback(unit_id, action)
        return JsonResponse({'status': 'success', 'new_status': action})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)