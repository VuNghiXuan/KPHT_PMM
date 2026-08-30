"""
File: apps/group_chat/views/knowledge_lifecycle_views.py
Mục đích: Quản lý vòng đời tri thức (Knowledge Lifecycle), phê duyệt KnowledgeUnit và KnowledgeChapter.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.group_chat.services.knowledge_service
"""

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Prefetch
from django.contrib import messages as django_messages
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit, KnowledgeChapter, Message, GroupMember
from apps.group_chat.services.knowledge_service import KnowledgeService
from apps.subscriptions.models import Subscription
from apps.core.models import Profile
from apps.ai_assistant.models import GroupAIProvider



logger = logging.getLogger(__name__)


@login_required
def knowledge_management(request, group_id):
    """Trang quản lý danh sách đơn vị tri thức và tài liệu theo nhóm."""
    group = get_object_or_404(ChatGroup, id=group_id)
    knowledge_units = KnowledgeUnit.objects.filter(document__group=group).select_related('document', 'document__uploaded_by')
    documents = Document.objects.filter(group=group).select_related('uploaded_by')

    context = {
        'group': group,
        'knowledge_units': knowledge_units,
        'documents': documents,
    }
    return render(request, 'group_chat/knowledge_management.html', context)


@login_required
@require_POST
def knowledge_action_view(request, group_id, knowledge_id, action):
    """Thực hiện phê duyệt hoặc hủy bỏ một KnowledgeUnit đơn lẻ."""
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id, document__group_id=group_id)
    membership = Membership.objects.filter(group_id=group_id, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': '🔒 Bạn không có quyền thực hiện tác vụ này trong nhóm!'}, status=403)

    if action == 'approve':
        ku.status = 'approved'
        ku.save(update_fields=['status'])
        return JsonResponse({'status': 'success', 'message': '✨ Đã duyệt tri thức và đồng bộ vào Vector DB!'})
        
    elif action in ['rollback', 'reject']:
        ku.delete()
        return JsonResponse({'status': 'success', 'message': '🗑️ Đã hủy tài liệu thành công!'})
        
    return JsonResponse({'status': 'error', 'message': '⚠️ Hành động không hợp lệ!'}, status=400)


@login_required
@require_POST
def promote_knowledge_view(request, message_id):
    """Đưa tin nhắn chat vào kho tri thức chờ duyệt (Pending)."""
    try:
        message = get_object_or_404(Message, id=message_id)
        membership = Membership.objects.filter(group=message.group, user=request.user).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': '🔒 Bạn không có quyền trong nhóm này'}, status=403)

        uploader_user = request.user
        if message.sender and hasattr(message.sender, 'user'):
            uploader_user = message.sender.user

        document = message.document
        if not document:
            document, _ = Document.objects.get_or_create(
                group=message.group,
                defaults={'uploaded_by': uploader_user, 'upload_type': 'chat'}
            )
        
        with transaction.atomic():
            knowledge_unit, created = KnowledgeUnit.objects.get_or_create(
                document=document,
                content=message.content,
                defaults={
                    'group': message.group, 
                    'status': 'pending'
                }
            )
            
            if not created and knowledge_unit.status == 'rollback':
                knowledge_unit.status = 'pending'
                knowledge_unit.content = message.content
                knowledge_unit.group = message.group
                knowledge_unit.save(update_fields=['status', 'content', 'group'])

        return JsonResponse({
            'status': 'success',
            'message': '🚀 Đã chuyển tin nhắn vào kho tri thức chờ duyệt thành công!',
            'knowledge_id': knowledge_unit.id
        })
    except Exception as e:
        logger.exception(f"❌ Lỗi promote knowledge: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)


@login_required
@require_POST
def rollback_knowledge(request, unit_id):
    """Đưa KnowledgeUnit về trạng thái hủy (rollback)."""
    unit = get_object_or_404(KnowledgeUnit, id=unit_id)
    group = unit.document.group if unit.document else getattr(unit, 'group', None)
    if not group:
        return JsonResponse({"error": "⚠️ Không tìm thấy thông tin nhóm liên kết."}, status=400)

    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership or getattr(membership, 'role', 'member') != 'admin':
        return JsonResponse({"error": "🔒 Bạn không có quyền quản trị!"}, status=403)

    try:
        with transaction.atomic():
            unit.status = 'rollback'
            unit.save(update_fields=['status'])
        return redirect('group_chat:knowledge_management', group_id=group.id)
    except Exception as e:
        logger.exception(f"❌ Lỗi rollback knowledge: {str(e)}")
        return JsonResponse({"error": f"Lỗi hệ thống: {str(e)}"}, status=500)


@login_required
def knowledge_chapter_list_view(request, group_id):
    """Liệt kê danh sách các chương tri thức (KnowledgeChapter) theo nhóm."""
    group = get_object_or_404(ChatGroup, id=group_id)
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': '🔒 Bạn không có quyền truy cập!'}, status=403)

    status_filter = request.GET.get('status', 'pending')
    chapters = KnowledgeService.get_pending_chapters(group_id) if status_filter == 'pending' else group.chapters.filter(status=status_filter)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        data = [{
            'id': ch.id,
            'title': ch.title,
            'summary': ch.summary,
            'status': ch.status,
            'confidence_score': getattr(ch, 'confidence_score', 1.0),
            'created_at': ch.created_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(ch, 'created_at', None) else ''
        } for ch in chapters]
        return JsonResponse({'status': 'success', 'chapters': data})

    context = {
        'group': group,
        'chapters': chapters,
        'current_status': status_filter
    }
    return render(request, 'group_chat/knowledge_chapter_management.html', context)


@login_required
@require_POST
def approve_reject_chapter_view(request, group_id, chapter_id):
    """Phê duyệt hoặc từ chối KnowledgeChapter với kiểm tra Tenant Isolation nghiêm ngặt."""
    # Kiểm tra group tồn tại
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # Kiểm tra quyền thành viên
    membership = Membership.objects.filter(group=group, user=request.user).exists()
    if not membership:
        return JsonResponse({'status': 'error', 'message': '🔒 Bạn không có quyền!'}, status=403)

    # 🛡️ Anti-Leakage: Chapter bắt buộc phải thuộc group_id hiện tại
    chapter = get_object_or_404(KnowledgeChapter, id=chapter_id, group_id=group_id)

    action = request.POST.get('action')
    if not action and request.body:
        try:
            body_data = json.loads(request.body)
            action = body_data.get('action')
        except json.JSONDecodeError:
            pass

    if action not in ['approve', 'reject']:
        return JsonResponse({'status': 'error', 'message': '⚠️ Hành động không hợp lệ.'}, status=400)

    new_status = 'approved' if action == 'approve' else 'rollback'
    try:
        # Service layer xử lý logic nghiệp vụ và signals
        result = KnowledgeService.update_chapter_status(chapter.id, new_status, request.user)
        return JsonResponse(result)
    except Exception as e:
        logger.exception(f"❌ Lỗi xử lý chapter action: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)

@login_required
def knowledge_dashboard_view(request, group_id):
    """Bảng điều khiển trung tâm quản lý tri thức (Tối ưu hóa Query Performance)."""
    chat_group = get_object_or_404(ChatGroup, id=group_id)
    
    membership = Membership.objects.filter(group=chat_group, user=request.user).first()
    if not membership:
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'trigger_learning':
            unit = KnowledgeService.synthesize_from_chat_group(chat_group)
            if unit:
                django_messages.success(request, "🎉 Đã tổng hợp thành công tri thức mới từ tin nhắn nhóm!")
            else:
                django_messages.info(request, "ℹ️ Không có tin nhắn mới nào cần học.")
            return redirect('group_chat:knowledge_dashboard', group_id=group_id)
            
        elif action == 'update_status':
            knowledge_id = request.POST.get('knowledge_id')
            new_status = request.POST.get('status')
            if not knowledge_id or not new_status:
                return JsonResponse({"status": "error", "message": "❌ Thiếu tham số!"}, status=400)
            try:
                KnowledgeService.update_knowledge_status(knowledge_id, new_status, request.user)
                return JsonResponse({"status": "success", "message": "✅ Cập nhật thành công!"})
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"❌ Lỗi: {str(e)}"}, status=500)

    # 🚀 TỐI ƯU HÓA TRUY VẤN: Sử dụng to_attr để cô lập namespace cache
    
    # 1. Messages: Prefetch sender profile riêng biệt
    # profile_queryset = Profile.objects.all()
    messages_query = chat_group.messages.select_related('sender').order_by('-created_at')[:50]
    messages_list = list(messages_query)
    messages_list.reverse()

    # 2. Documents & Knowledge Units
    documents = list(Document.objects.filter(group=chat_group).select_related('uploaded_by').order_by('-uploaded_at'))
    pending_knowledge_units = list(KnowledgeUnit.objects.filter(document__group=chat_group, status='pending').select_related('document').order_by('-id'))
    approved_knowledge_units = list(KnowledgeUnit.objects.filter(document__group=chat_group, status='approved').select_related('document').order_by('-id'))
    
    # 3. Memberships: Prefetch user profile riêng biệt
    # 3. Memberships: Chỉ dùng select_related, loại bỏ Prefetch để tránh xung đột Registry
    memberships = list(
        Membership.objects.filter(group=chat_group)
        .select_related('user', 'user__profile') # Dùng select_related trực tiếp cho OneToOne
    )
    
    context = {
        'group': chat_group,
        'chat_group': chat_group,
        'membership': membership,
        'messages': messages_list,
        'memberships': memberships,
        'documents': documents,
        'pending_knowledge_units': pending_knowledge_units,
        'approved_knowledge_units': approved_knowledge_units,
        'subscription': Subscription.objects.filter(group=chat_group).first(),
        'ai_config': GroupAIProvider.objects.filter(group=chat_group).first(),
    }
    return render(request, 'group_chat/knowledge_dashboard.html', context)
