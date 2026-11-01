# File: apps/group_chat/views/feedback_views.py

"""
Mục đích: Xử lý tương tác cảm xúc (Feedback Loop), thả Like/Heart/Dislike cho tin nhắn 
          và cung cấp API chi tiết cảm xúc kiểu Zalo, đảm bảo tính năng Group-Centric.
Module liên kết: apps.group_chat.models (Membership, Message, MessageFeedback)
"""

import json
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from apps.group_chat.models import Membership, Message, MessageFeedback
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
@require_POST
def knowledge_feedback_view(request, message_id):
    """
    Function: knowledge_feedback_view
    Description: Xử lý thả cảm xúc (Like, Heart, Dislike) cho tin nhắn theo phong cách Zalo.
    Giải thích logic (Why):
        - Kiểm tra Tenant Isolation qua Membership để bảo mật quyền hạn trong nhóm.
        - Sử dụng trường 'user' và 'type' khớp chuẩn cơ sở dữ liệu hiện tại.
    """
    message = get_object_or_404(Message, id=message_id)    
    
    # Kiểm tra quyền thành viên trong nhóm làm việc (Tenant Isolation)
    membership = request.user.memberships.filter(group=message.group).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này!'}, status=403)

    try:
        data = json.loads(request.body)
        feedback_type = data.get('type')
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ!'}, status=400)

    if feedback_type not in ['like', 'heart', 'dislike']:
        return JsonResponse({'status': 'error', 'message': 'Loại cảm xúc không hợp lệ!'}, status=400)

    # Kiểm tra xem user đã thả cảm xúc trên tin nhắn này chưa (khớp chuẩn DB: message & user)
    existing_feedback = MessageFeedback.objects.filter(message=message, user=request.user).first()
    
    if existing_feedback:
        if existing_feedback.type == feedback_type:
            existing_feedback.delete()  # Toggle off: Bỏ cảm xúc nếu click lại loại cũ
        else:
            existing_feedback.type = feedback_type
            existing_feedback.save()    # Đổi loại cảm xúc mới
    else:
        # Tạo mới bản ghi feedback đúng chuẩn schema hiện tại của bảng MessageFeedback
        MessageFeedback.objects.create(
            group=message.group,
            message=message,
            user=request.user,
            type=feedback_type
        )

    # Chuẩn bị dữ liệu trả về cho Front-end cập nhật qua WebSocket / AJAX
    all_feedbacks = message.feedbacks.select_related('user').all()
    total_count = all_feedbacks.count()

    icons_map = {'like': '👍', 'heart': '❤️', 'dislike': '👎'}
    grouped_icons = list(all_feedbacks.values_list('type', flat=True).distinct())
    rendered_icons = [icons_map[t] for t in grouped_icons if t in icons_map]

    feedback_details = []
    for fb in all_feedbacks:
        feedback_details.append({
            'username': fb.user.username if fb.user else "AI Assistant",
            'type': fb.type,
            'icon': icons_map.get(fb.type, '')
        })

    return JsonResponse({
        'status': 'success',
        'total_count': total_count,
        'rendered_icons': rendered_icons,
        'feedbacks': feedback_details
    })


@login_required
def message_reactions_detail_view(request, message_id):
    """
    Function: message_reactions_detail_view
    Description: Trả về danh sách chi tiết các lượt tương tác phục vụ hiển thị Modal.
    """
    message = get_object_or_404(Message, id=message_id)

    # Kiểm tra quyền thành viên trong nhóm
    membership = request.user.memberships.filter(group=message.group).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này!'}, status=403)

    feedbacks = MessageFeedback.objects.filter(message=message).select_related('user')
    total_count = feedbacks.count()

    icons_map = {'like': '👍', 'heart': '❤️', 'dislike': '👎'}
    feedback_details = []

    for fb in feedbacks:
        username = fb.user.username if fb.user else "AI Assistant"
        feedback_details.append({
            'username': username,
            'type': fb.type,
            'icon': icons_map.get(fb.type, '')
        })

    return JsonResponse({
        'status': 'success',
        'total_count': total_count,
        'feedbacks': feedback_details
    })


@login_required
@require_POST
def handle_message_feedback_ajax(request, message_id):
    """
    Function: handle_message_feedback_ajax
    Description: Xử lý thả cảm xúc qua AJAX tương thích hoàn toàn với schema database.
    """
    try:
        data = json.loads(request.body)
        feedback_type = data.get('type')
        
        if feedback_type not in ['like', 'heart', 'dislike']:
            return JsonResponse({'status': 'error', 'message': 'Loại tương tác không hợp lệ.'}, status=400)
        
        message = get_object_or_404(Message, id=message_id)
        
        # Kiểm tra Membership của user trong nhóm chứa tin nhắn (Group-Centric)
        membership = request.user.memberships.filter(group=message.group).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': 'Bạn không phải thành viên của nhóm này.'}, status=403)
        
        # Truy vấn với trường user và type chuẩn xác theo cơ sở dữ liệu
        existing_feedback = MessageFeedback.objects.filter(
            message=message, 
            user=request.user, 
            type=feedback_type
        ).first()
        
        if existing_feedback:
            existing_feedback.delete()
            action = 'removed'
        else:
            MessageFeedback.objects.create(
                group=message.group,
                message=message,
                user=request.user,
                type=feedback_type
            )
            action = 'added'
            
        reactions_count = {
            'like': message.feedbacks.filter(type='like').count(),
            'heart': message.feedbacks.filter(type='heart').count(),
            'dislike': message.feedbacks.filter(type='dislike').count(),
        }
        total_count = message.feedbacks.count()
        
        return JsonResponse({
            'status': 'success',
            'action': action,
            'reactions_count': reactions_count,
            'total_count': total_count,
        })
        
    except Exception as e:
        logger.error(f"❌ Lỗi feedback AJAX: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)