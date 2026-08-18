

# File: apps/group_chat/views/chat_views.py
"""
Mục đích: Xử lý phòng chat, chi tiết nhóm, tin nhắn real-time và bảo mật theo Tenant group_id.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from apps.group_chat.models import ChatGroup, Membership, Message, KnowledgeUnit
from apps.subscriptions.models import Subscription


@login_required
def create_group(request):
    """
    Function: create_group
    Description: 
        Xử lý yêu cầu tạo mới một nhóm làm việc (ChatGroup). 
        Mỗi nhóm được xem như một thực thể cô lập (Tenant-based Isolation) theo mô hình Group-Centric.
        Sau khi tạo thành công, hệ thống tự động gán user hiện tại làm Admin,
        khởi tạo gói cước và điều hướng trực tiếp vào phòng chat chi tiết của nhóm.
    Module liên kết: apps.group_chat.models, apps.group_chat.forms
    """
    if request.method == 'POST':
        group_name = request.POST.get('name')
        if group_name:
            # 1. Khởi tạo ChatGroup mới
            group = ChatGroup.objects.create(name=group_name)
            
            # 2. Gán người tạo làm quản trị viên (Admin) của nhóm
            Membership.objects.create(
                user=request.user,
                group=group,
                role='admin'
            )
            
            # 3. Điều hướng chính xác vào route 'group_detail' kèm theo tham số group_id
            return redirect('group_chat:group_detail', group_id=group.id)
            
    return render(request, 'group_chat/create.html')

@login_required
def group_chat_detail(request, group_id):
    """
    Function: group_chat_detail
    Description: 
        Hiển thị giao diện chat chính của nhóm. Nếu người dùng xóa hết nhóm 
        hoặc không tìm thấy nhóm, hệ thống sẽ tự động điều hướng về trang 
        tạo nhóm mới hoặc dashboard để tránh lỗi 404.
    """
    # 1. Kiểm tra xem user có thuộc nhóm nào không, nếu không có nhóm nào -> chuyển hướng tạo nhóm
    user_groups = ChatGroup.objects.filter(memberships__user=request.user)
    if not user_groups.exists():
        return redirect('group_chat:create_group')

    # 2. Lấy thông tin nhóm an toàn
    group = ChatGroup.objects.filter(id=group_id).first()
    if not group:
        first_group = user_groups.first()
        return redirect('group_chat:group_detail', group_id=first_group.id)
    
    # 3. Xác thực xem user hiện tại có phải là thành viên hợp lệ của nhóm này không
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership:
        valid_group = user_groups.first()
        if valid_group:
            return redirect('group_chat:group_detail', group_id=valid_group.id)
        return redirect('group_chat:create_group')
    
    # 4. Truy vấn tin nhắn và dữ liệu liên quan
    messages = list(group.messages.select_related('sender').order_by('-created_at')[:50])
    messages.reverse()
    
    memberships = group.memberships.select_related('user', 'user__profile').all()
    documents = group.documents.all().order_by('-uploaded_at')
    knowledge_units = KnowledgeUnit.objects.filter(document__group=group).order_by('-id')

    subscription = getattr(group, 'subscription', None)
    ai_config = getattr(group, 'aiconfig', None)

    context = {
        'group': group,
        'chat_group': group,  # Bổ sung đồng bộ tuyệt đối tránh lỗi VariableDoesNotExist cho template partials[cite: 1]
        'membership': membership,
        'messages': messages,
        'memberships': memberships,
        'documents': documents,
        'knowledge_units': knowledge_units,
        'subscription': subscription,
        'ai_config': ai_config,
    }
    
    return render(request, 'group_chat/group_detail.html', context)