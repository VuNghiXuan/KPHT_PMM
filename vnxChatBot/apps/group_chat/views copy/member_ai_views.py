# File: apps/group_chat/views/member_ai_views.py
"""
Mục đích: Quản lý thêm thành viên vào nhóm, lấy danh sách thành viên qua API 
và cấu hình AI riêng biệt cho từng nhóm (Group-Centric AI Configuration).
"""


import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from apps.group_chat.models import ChatGroup, Membership
from apps.ai_assistant.models import GroupAIProvider
from apps.core.models import User
from apps.subscriptions.models import Subscription
from django.contrib.auth import get_user_model

User = get_user_model()
# Khởi tạo logger để theo dõi debug
logger = logging.getLogger(__name__)

@login_required
@require_POST
def add_member_to_group(request, group_id):
    """
    Function: add_member_to_group
    Description: 
        Xử lý yêu cầu thêm thành viên mới vào nhóm làm việc (ChatGroup) thông qua chuẩn JSON API.
        Hàm này gộp chung logic kiểm tra quyền quản trị (owner/admin), tìm kiếm linh hoạt 
        qua username hoặc email, kiểm tra giới hạn gói cước (Subscription), và đảm bảo 
        luôn trả về định dạng JSON an toàn cho phía client.
    
    Module liên kết: apps.group_chat.models, apps.subscriptions.models
    """
    # 1. Lấy thông tin nhóm theo cơ chế Tenant-based Isolation
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # 2. Kiểm tra quyền quản trị qua Membership (Chỉ owner hoặc admin mới được thêm thành viên)
    is_admin = Membership.objects.filter(
        group=group, 
        user=request.user, 
        role__in=['owner', 'admin']
    ).exists()
    
    if not is_admin:
        return JsonResponse({
            'status': 'error', 
            'message': 'Bạn không có quyền quản trị để thêm thành viên vào nhóm này!'
        }, status=403)

    try:
        # 3. Phân tích dữ liệu JSON từ request body
        data = json.loads(request.body)
        identifier = data.get('username') or data.get('email')
        role = data.get('role', 'member') # Mặc định là thành viên thông thường
        
        if not identifier:
            return JsonResponse({
                'status': 'error', 
                'message': 'Vui lòng cung cấp username hoặc email của thành viên cần thêm!'
            }, status=400)
        
        # 4. Tìm kiếm user linh hoạt bằng cả username hoặc email
        user_to_add = User.objects.filter(username=identifier).first() or User.objects.filter(email=identifier).first()
        
        if not user_to_add:
            return JsonResponse({
                'status': 'error', 
                'message': f'Không tìm thấy người dùng với thông tin: {identifier}'
            }, status=404)
            
        # 5. Kiểm tra xem người dùng đã là thành viên của nhóm hay chưa
        if Membership.objects.filter(group=group, user=user_to_add).exists():
            return JsonResponse({
                'status': 'error', 
                'message': 'Người dùng này đã là thành viên của nhóm!'
            }, status=400)
            
        # 6. Kiểm tra giới hạn gói cước Subscription (Group-Centric)
        subscription, _ = Subscription.objects.get_or_create(group=group)
        current_members_count = Membership.objects.filter(group=group).count()
        max_allowed_members = getattr(subscription, 'max_members', getattr(subscription, 'max_users', 6))
        
        if current_members_count >= max_allowed_members:
            return JsonResponse({
                'status': 'error', 
                'message': f'Nhóm đã đạt giới hạn tối đa ({max_allowed_members} thành viên) theo gói cước hiện tại!'
            }, status=400)
            
        # 7. Tạo bản ghi Membership mới cho thành viên
        Membership.objects.create(group=group, user=user_to_add, role=role)
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Đã thêm thành viên {user_to_add.username} vào nhóm thành công!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error', 
            'message': 'Dữ liệu gửi lên không đúng định dạng JSON chuẩn.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': f'Lỗi hệ thống nội bộ: {str(e)}'
        }, status=500)

    
@login_required
def get_group_members_api(request, group_id):
    """
    API trả về danh sách thành viên và AI trong nhóm dưới dạng JSON
    phục vụ tính năng gán thẻ (@mention) trên giao diện chat.
    """
    try:
        chat_group = ChatGroup.objects.get(id=group_id)
        # Kiểm tra quyền thành viên (Tenant Isolation theo ChatGroup)
        if not Membership.objects.filter(group=chat_group, user=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Không có quyền truy cập'}, status=403)
        
        memberships = Membership.objects.filter(group=chat_group).select_related('user__profile')
        
        members_data = []
        for m in memberships:
            if m.is_ai:
                members_data.append({
                    'id': 'ai',
                    'name': 'AI Assistant',
                    'username': 'ai',
                    'is_ai': True,
                    'avatar': '🤖'
                })
            elif m.user:
                avatar_url = m.user.profile.avatar.url if hasattr(m.user, 'profile') and m.user.profile.avatar else None
                members_data.append({
                    'id': m.user.id,
                    'name': m.user.get_full_name() or m.user.username,
                    'username': m.user.username,
                    'is_ai': False,
                    'avatar': avatar_url
                })
                
        return JsonResponse({'status': 'success', 'members': members_data})
    except ChatGroup.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Nhóm không tồn tại'}, status=404)



@login_required
def update_ai_config_view(request, group_id):
    """
    Cập nhật cấu hình AI riêng cho nhóm (Group-Centric AI Configuration).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)
        
    group = get_object_or_404(ChatGroup, id=group_id)
    try:
        data = json.loads(request.body)
        ai_config, created = GroupAIProvider.objects.get_or_create(group=group)
        ai_config.provider = data.get('provider', 'gemini')
        ai_config.temperature = float(data.get('temperature', 0.7))
        ai_config.system_prompt = data.get('system_prompt', '')
        ai_config.save()
        
        return JsonResponse({'status': 'success', 'message': 'Cập nhật cấu hình AI thành công!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)




