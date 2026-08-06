# File: apps/group_chat/views/feedback_views.py
"""
Mục đích: Xử lý tương tác cảm xúc (Feedback Loop), thả Like/Heart/Dislike cho tin nhắn 
và cung cấp API chi tiết cảm xúc kiểu Zalo.
"""

import json
import logging
from django.shortcuts import  get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from apps.group_chat.models import  Membership, Message, MessageFeedback
from django.contrib.auth import get_user_model

User = get_user_model()
# Khởi tạo logger để theo dõi debug
logger = logging.getLogger(__name__)



@login_required
@require_POST
def knowledge_feedback_view(request, message_id):
    """
    Mục đích: Xử lý thả cảm xúc (Like, Heart, Dislike) cho tin nhắn theo phong cách Zalo.
    Module liên kết: apps.group_chat.models (Message, MessageFeedback)
    
    Giải thích logic (Why):
    - Đảm bảo tính năng Group-Centric: Kiểm tra user có thuộc quyền membership trong nhóm chứa tin nhắn hay không.
    - Xử lý Toggle cảm xúc: Nếu user đã thả cùng loại cảm xúc thì hủy (delete), nếu khác loại thì cập nhật, nếu chưa có thì tạo mới gắn với user.
    """
    message = get_object_or_404(Message, id=message_id)    
    
    # Kiểm tra quyền thành viên trong nhóm làm việc (Tenant Isolation)
    membership = request.user.memberships.filter(group=message.group).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

    try:
        data = json.loads(request.body)
        feedback_type = data.get('type')
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ'}, status=400)

    if feedback_type not in ['like', 'heart', 'dislike']:
        return JsonResponse({'status': 'error', 'message': 'Loại cảm xúc không hợp lệ'}, status=400)

    # Kiểm tra xem user đã thả cảm xúc trên tin nhắn này chưa (Model MessageFeedback liên kết qua user và group)
    existing_feedback = MessageFeedback.objects.filter(message=message, user=request.user).first()
    
    if existing_feedback:
        if existing_feedback.type == feedback_type:
            existing_feedback.delete()  # Click lần nữa để bỏ cảm xúc (Toggle off)
        else:
            existing_feedback.type = feedback_type
            existing_feedback.save()    # Thay đổi loại cảm xúc
    else:
        # Tạo mới bản ghi feedback gắn kết trực tiếp với group và user theo chuẩn database schema
        MessageFeedback.objects.create(
            group=message.group,
            message=message,
            user=request.user,
            type=feedback_type
        )

    # Chuẩn bị dữ liệu trả về cho Front-end cập nhật tức thời qua WebSocket / AJAX
    all_feedbacks = message.feedbacks.select_related('user').all()
    total_count = all_feedbacks.count()

    # Gom nhóm các loại icon đang có hiển thị trên giao diện
    feedback_details = []
    icons_map = {'like': '👍', 'heart': '❤️', 'dislike': '👎'}
    
    grouped_icons = list(all_feedbacks.values_list('type', flat=True).distinct())
    rendered_icons = [icons_map[t] for t in grouped_icons if t in icons_map]

    for fb in all_feedbacks:
        feedback_details.append({
            'username': fb.user.username if fb.user else "AI",
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
    Mục đích: Trả về danh sách chi tiết các lượt tương tác (Like, Heart, Dislike) của tin nhắn.
    Module liên kết: apps.group_chat.models (Message, MessageFeedback)
    
    Giải thích logic (Why):
    - Đã lược bỏ các ký tự đặc biệt/emoji khỏi câu lệnh logger để tương thích hoàn toàn 
      với bảng mã CP1252 mặc định trên Windows Terminal, tránh lỗi UnicodeEncodeError rác.
    - Truy vấn chuẩn xác các bản ghi MessageFeedback dựa trên message_id để hiển thị đúng 
      số lượng và icon tương ứng lên modal giao diện.
    """
    logger.info(f"==> [DEBUG] Bat dau xu ly reactions-detail cho message_id={message_id} boi user='{request.user.username}'")
    
    # 1. Lấy thông tin tin nhắn
    message = get_object_or_404(Message, id=message_id)
    logger.info(f"==> [DEBUG] Tim thay tin nhắn ID {message.id} thuoc ChatGroup ID {message.group.id}")

    # 2. Kiểm tra quyền thành viên trong nhóm (Tenant Isolation)
    membership = request.user.memberships.filter(group=message.group).first()
    if not membership:
        logger.warning(f"==> [WARN] User khong co quyền trong nhóm nay")
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

    # 3. Truy vấn toàn bộ feedback gắn với message này
    feedbacks = MessageFeedback.objects.filter(message=message).select_related('user')
    total_count = feedbacks.count()
    logger.info(f"==> [DEBUG] Tong so luong feedbacks tim thay trong DB: {total_count}")

    icons_map = {'like': '👍', 'heart': '❤️', 'dislike': '👎'}
    feedback_details = []

    for fb in feedbacks:
        username = fb.user.username if fb.user else "AI"
        icon = icons_map.get(fb.type, '')
        # Lưu ý: Không đưa biến 'icon' vào logger để tránh lỗi mã hóa Windows console
        logger.info(f"    + Feedback: User={username}, Type={fb.type}")
        feedback_details.append({
            'username': username,
            'type': fb.type,
            'icon': icon
        })

    response_data = {
        'status': 'success',
        'total_count': total_count,
        'feedbacks': feedback_details
    }
    
    logger.info(f"==> [DEBUG] Tra ve du lieu thanh cong cho client.")
    return JsonResponse(response_data)

@login_required
def handle_message_feedback_ajax(request, message_id):
    """
    Xử lý thả cảm xúc (Like, Heart, Dislike) cho tin nhắn qua AJAX.
    
    Logic nghiệp vụ:
        - Kiểm tra thành viên thuộc nhóm (Tenant Isolation).
        - Toggle cảm xúc: Nếu đã tồn tại -> Xóa (Hủy thả), nếu chưa -> Tạo mới.
        - Trả về tổng số lượng chi tiết để client cập nhật giao diện trực quan.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_type = data.get('type') # Các giá trị hỗ trợ: 'like', 'heart', 'dislike'
            
            valid_feedback_types = ['like', 'heart', 'dislike']
            if feedback_type not in valid_feedback_types:
                return JsonResponse({'status': 'error', 'message': 'Loại tương tác không hợp lệ.'}, status=400)
            
            message = Message.objects.get(id=message_id)
            
            # Kiểm tra Membership của user trong nhóm chứa tin nhắn (Group-Centric)
            membership = Membership.objects.filter(user=request.user, group=message.group).first()
            if not membership:
                return JsonResponse({'status': 'error', 'message': 'Bạn không phải thành viên của nhóm này.'}, status=403)
            
            # Kiểm tra xem user đã thả cảm xúc này chưa
            existing_feedback = MessageFeedback.objects.filter(
                message=message, 
                member=membership, 
                feedback_type=feedback_type
            ).first()
            
            if existing_feedback:
                existing_feedback.delete()
                action = 'removed'
            else:
                MessageFeedback.objects.create(
                    message=message,
                    member=membership,
                    feedback_type=feedback_type
                )
                action = 'added'
                
            # Thống kê số lượng chi tiết cho từng loại cảm xúc
            reactions_count = {
                'like': message.feedbacks.filter(feedback_type='like').count(),
                'heart': message.feedbacks.filter(feedback_type='heart').count(),
                'dislike': message.feedbacks.filter(feedback_type='dislike').count(),
            }
            total_count = message.feedbacks.count()
            
            return JsonResponse({
                'status': 'success',
                'action': action,
                'reactions_count': reactions_count,
                'total_count': total_count,
            })
            
        except Message.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tin nhắn.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Phương thức không được hỗ trợ.'}, status=405)

