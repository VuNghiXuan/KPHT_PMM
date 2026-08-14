"""
File: apps/group_chat/views/knowledge_lifecycle_views.py
Mục đích: Quản lý vòng đời tri thức (Knowledge Lifecycle), phê duyệt KnowledgeUnit và KnowledgeChapter.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages

from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit, Message
from apps.group_chat.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


@login_required
def knowledge_management(request, group_id):
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
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id, document__group_id=group_id)
    membership = Membership.objects.filter(group_id=group_id, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thực hiện tác vụ này trong nhóm!'}, status=403)

    if action == 'approve':
        ku.status = 'approved'
        ku.save()
        return JsonResponse({'status': 'success', 'message': 'Đã duyệt tri thức và đồng bộ vào Vector DB!'})
        
    elif action in ['rollback', 'reject']:
        ku.delete()
        return JsonResponse({'status': 'success', 'message': 'Đã hủy tài liệu thành công!'})
        
    return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ!'}, status=400)


@login_required
@require_POST
def promote_knowledge_view(request, message_id):
    try:
        message = get_object_or_404(Message, id=message_id)
        membership = Membership.objects.filter(group=message.group, user=request.user).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

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
                knowledge_unit.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Đã chuyển tin nhắn vào kho tri thức chờ duyệt thành công!',
            'knowledge_id': knowledge_unit.id
        })
    except Exception as e:
        logger.error(f"❌ Lỗi promote knowledge: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)


@login_required
@require_POST
def rollback_knowledge(request, unit_id):
    unit = get_object_or_404(KnowledgeUnit, id=unit_id)
    group = unit.document.group if unit.document else getattr(unit, 'group', None)
    if not group:
        return JsonResponse({"error": "Không tìm thấy thông tin nhóm liên kết."}, status=400)

    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership or getattr(membership, 'role', 'member') != 'admin':
        return JsonResponse({"error": "Bạn không có quyền quản trị!"}, status=403)

    try:
        with transaction.atomic():
            unit.status = 'rollback'
            unit.save()
        return redirect('group_chat:knowledge_management', group_id=group.id)
    except Exception as e:
        return JsonResponse({"error": f"Lỗi hệ thống: {str(e)}"}, status=500)


@login_required
def knowledge_chapter_list_view(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền truy cập!'}, status=403)

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
    group = get_object_or_404(ChatGroup, id=group_id)
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền!'}, status=403)

    action = request.POST.get('action')
    if action not in ['approve', 'reject']:
        return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ.'}, status=400)

    new_status = 'approved' if action == 'approve' else 'rollback'
    try:
        result = KnowledgeService.update_chapter_status(chapter_id, new_status, request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)


@login_required
def knowledge_dashboard_view(request, group_id):
    chat_group = get_object_or_404(ChatGroup, id=group_id)
    if not chat_group.membership_set.filter(user=request.user).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'trigger_learning':
            unit = KnowledgeService.synthesize_from_chat_group(chat_group)
            if unit:
                messages.success(request, "Đã tổng hợp thành công tri thức mới từ tin nhắn nhóm!")
            else:
                messages.info(request, "Không có tin nhắn mới nào cần học.")
            return redirect('knowledge_dashboard', group_id=group_id)
            
        elif action == 'update_status':
            knowledge_id = request.POST.get('knowledge_id')
            new_status = request.POST.get('status')
            KnowledgeService.update_knowledge_status(knowledge_id, new_status, request.user)
            return JsonResponse({"status": "success", "message": "Cập nhật trạng thái thành công!"})

    documents = Document.objects.filter(group=chat_group).order_by('-uploaded_at')
    knowledge_units = KnowledgeUnit.objects.filter(group=chat_group).order_by('-created_at')

    context = {
        'chat_group': chat_group,
        'documents': documents,
        'knowledge_units': knowledge_units,
    }
    return render(request, 'group_chat/knowledge_dashboard.html', context)