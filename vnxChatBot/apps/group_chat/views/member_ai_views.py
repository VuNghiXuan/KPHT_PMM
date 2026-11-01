# File: apps/group_chat/views/member_ai_views.py
"""
Mục đích: Quản lý thêm thành viên vào nhóm, lấy danh sách thành viên qua API 
và cấu hình AI riêng biệt cho từng nhóm (Group-Centric AI Configuration).
Tác giả: Kiến trúc sư VnxChatBot
"""

import json
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth import get_user_model

from apps.group_chat.models import ChatGroup, Membership
from apps.ai_assistant.models.groupAI import GroupAIProvider
from apps.subscriptions.models import Subscription
from apps.ai_assistant.services.llm_provider import LLMService

User = get_user_model()
logger = logging.getLogger(__name__)

# Model mặc định an toàn cho từng nhà cung cấp
DEFAULT_MODELS = {
    'gemini': 'gemini-2.0-flash',
    'groq': 'qwen/qwen3.8-27b',
    'ollama': 'qwen2.5:7b',
    'openai': 'gpt-4o-mini',
}


@login_required
@require_POST
def add_member_to_group(request, group_id):
    """
    Function: add_member_to_group
    Description: 
        Xử lý yêu cầu thêm thành viên mới vào nhóm làm việc (ChatGroup) thông qua JSON API.
        Tối ưu truy vấn tìm kiếm user bằng Q object và kiểm tra giới hạn Subscription.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # 1. Kiểm tra quyền quản trị (owner hoặc admin)
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
        data = json.loads(request.body)
        identifier = (data.get('username') or data.get('email') or '').strip()
        role = data.get('role', 'member')

        if not identifier:
            return JsonResponse({
                'status': 'error', 
                'message': 'Vui lòng cung cấp username hoặc email của thành viên cần thêm!'
            }, status=400)
        
        # 2. Tối ưu truy vấn: Tìm user bằng Q object trong 1 câu lệnh SQL đơn
        user_to_add = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        
        if not user_to_add:
            return JsonResponse({
                'status': 'error', 
                'message': f'Không tìm thấy người dùng với thông tin: {identifier}'
            }, status=404)
            
        # 3. Kiểm tra sự tồn tại trong nhóm
        if Membership.objects.filter(group=group, user=user_to_add).exists():
            return JsonResponse({
                'status': 'error', 
                'message': 'Người dùng này đã là thành viên của nhóm!'
            }, status=400)
            
        # 4. Kiểm tra giới hạn gói cước Subscription
        subscription, _ = Subscription.objects.get_or_create(group=group)
        current_members_count = Membership.objects.filter(group=group).count()
        max_allowed_members = getattr(subscription, 'max_members', getattr(subscription, 'max_users', 6))
        
        if current_members_count >= max_allowed_members:
            return JsonResponse({
                'status': 'error', 
                'message': f'Nhóm đã đạt giới hạn tối đa ({max_allowed_members} thành viên) theo gói cước hiện tại!'
            }, status=400)
            
        # 5. Khởi tạo bản ghi Membership
        Membership.objects.create(group=group, user=user_to_add, role=role)
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Đã thêm thành viên {user_to_add.username} vào nhóm thành công!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu không đúng định dạng JSON chuẩn.'}, status=400)
    except Exception as e:
        logger.error(f"Lỗi khi thêm thành viên vào group {group_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống nội bộ: {str(e)}'}, status=500)


@login_required
def get_group_members_api(request, group_id):
    """
    API trả về danh sách thành viên và AI trong nhóm dưới dạng JSON
    phục vụ tính năng gán thẻ (@mention) trên giao diện chat.
    """
    try:
        chat_group = ChatGroup.objects.get(id=group_id)
        
        # Kiểm tra quyền thành viên (Tenant Isolation)
        if not Membership.objects.filter(group=chat_group, user=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Không có quyền truy cập'}, status=403)
        
        memberships = Membership.objects.filter(group=chat_group).select_related('user__profile')
        
        members_data = []
        for m in memberships:
            if getattr(m, 'is_ai', False):
                members_data.append({
                    'id': 'ai',
                    'name': 'AI Assistant',
                    'username': 'ai',
                    'is_ai': True,
                    'avatar': '🤖'
                })
            elif m.user:
                avatar_url = None
                if hasattr(m.user, 'profile') and m.user.profile.avatar:
                    avatar_url = m.user.profile.avatar.url

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
@require_POST
def update_ai_config_view(request, group_id):
    """
    Mục đích: Cập nhật cấu hình AI riêng biệt cho từng nhóm làm việc.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    if not Membership.objects.filter(group=group, user=request.user, role__in=['owner', 'admin']).exists():
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thay đổi cấu hình AI của nhóm này!'}, status=403)

    try:
        data = json.loads(request.body)
        provider = data.get('ai_provider', 'gemini').strip().lower()
        model = data.get('ai_model', '').strip()
        custom_key = data.get('custom_api_key')

        allowed_providers = ['gemini', 'groq', 'ollama', 'openai']
        if provider not in allowed_providers:
            return JsonResponse({'status': 'error', 'message': 'Nhà cung cấp AI (Provider) không hợp lệ!'}, status=400)

        ai_config, _ = GroupAIProvider.objects.get_or_create(group=group)
        ai_config.provider = provider
        
        # Gán model name hoặc sử dụng model mặc định
        ai_config.model_name = model if model else DEFAULT_MODELS.get(provider, 'gemini-2.0-flash')
            
        # Xử lý API Key: Với Ollama, gán 'ollama' để AIFactory & LiteLLM nhận diện hợp lệ
        if custom_key is None or str(custom_key).strip() == "":
            ai_config.api_key = "ollama" if provider == 'ollama' else None 
        else:
            ai_config.api_key = str(custom_key).strip()
            
        ai_config.save()
        
        logger.info(f"Group {group_id} đã cập nhật cấu hình AI: Provider={provider}, Model={ai_config.model_name}")
        return JsonResponse({'status': 'success', 'message': 'Cập nhật cấu hình Trợ lý AI thành công! 🚀'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ!'}, status=400)
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật AI config cho nhóm {group_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Đã xảy ra lỗi hệ thống nội bộ!'}, status=500)


@login_required
@require_POST
def validate_and_test_ai_model(request, group_id):
    """
    Mục đích: Kiểm tra tính hợp lệ và kết nối thực tế tới LLM Provider 
    thông qua LLMService.validate_provider_key trước khi thực hiện lưu.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    if not Membership.objects.filter(group=group, user=request.user, role__in=['owner', 'admin']).exists():
        return JsonResponse({'status': 'error', 'message': 'Không có quyền thực thi!'}, status=403)

    try:
        data = json.loads(request.body)
        provider = data.get('ai_provider', '').strip().lower()
        model_name = data.get('ai_model', '').strip() or DEFAULT_MODELS.get(provider, '')
        api_key = data.get('custom_api_key', '').strip()

        if provider == 'ollama' and not api_key:
            api_key = 'ollama'

        # Gọi trực tiếp service kiểm tra kết nối tập trung (DRY principle)
        is_valid = LLMService.validate_provider_key(
            provider=provider, 
            api_key=api_key, 
            model_name=model_name
        )

        if is_valid:
            return JsonResponse({
                'status': 'success',
                'message': f"Xác thực thành công model '{model_name}' cho {provider.upper()}! 🚀"
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f"Kiểm tra thất bại! Vui lòng kiểm tra lại API Key hoặc tên Model '{model_name}'."
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ!'}, status=400)
    except Exception as e:
        logger.error(f"Lỗi validate AI model: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi kiểm tra model: {str(e)}'}, status=500)