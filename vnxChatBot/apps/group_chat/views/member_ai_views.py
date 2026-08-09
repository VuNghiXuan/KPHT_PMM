# File: apps/group_chat/views/member_ai_views.py
"""
Mục đích: Quản lý thêm thành viên vào nhóm, lấy danh sách thành viên qua API 
và cấu hình AI riêng biệt cho từng nhóm (Group-Centric AI Configuration).
"""


import json
import logging
import requests
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
@require_POST
def update_ai_config_view(request, group_id):
    """
    Mục đích: Cập nhật cấu hình AI riêng biệt cho từng nhóm làm việc.
    Flow: 
        1. Kiểm tra quyền quản trị (Owner/Admin) trong phạm vi group_id (Group-Centric).
        2. Validate dữ liệu đầu vào (Provider và Model Name).
        3. Lưu trữ an toàn vào database thông qua model GroupAIProvider (sử dụng model_name).
    """
    # 1. Isolation: Cô lập tuyệt đối theo group_id và kiểm tra quyền hạn
    group = get_object_or_404(ChatGroup, id=group_id)
    if not Membership.objects.filter(group=group, user=request.user, role__in=['owner', 'admin']).exists():
        return JsonResponse({
            'status': 'error', 
            'message': 'Bạn không có quyền thay đổi cấu hình AI của nhóm này!'
        }, status=403)

    try:
        data = json.loads(request.body)
        
        # 2. Extract dữ liệu với giá trị mặc định an toàn
        provider = data.get('ai_provider', 'gemini').strip().lower()
        model = data.get('ai_model', '').strip()
        custom_key = data.get('custom_api_key') # Có thể là string, rỗng hoặc null

        # 3. Validate nhà cung cấp hợp lệ
        allowed_providers = ['gemini', 'groq', 'ollama', 'openai']
        if provider not in allowed_providers:
            return JsonResponse({
                'status': 'error', 
                'message': 'Nhà cung cấp AI (Provider) không hợp lệ!'
            }, status=400)

        # 4. Cập nhật hoặc tạo mới cấu hình GroupAIProvider (1:1 với ChatGroup)
        ai_config, _ = GroupAIProvider.objects.get_or_create(group=group)
        
        ai_config.provider = provider
        
        # Đồng bộ gán vào trường model_name của Database Model
        if model:
            ai_config.model_name = model
            
        # 5. Logic xử lý API Key (Security)
        # Nếu data gửi lên là None hoặc rỗng, xóa key cũ để hệ thống dùng key chung
        if custom_key is None or custom_key == "":
            ai_config.api_key = None 
        else:
            ai_config.api_key = custom_key.strip()
            
        ai_config.save()
        
        logger.info(f"Group {group_id} đã cập nhật cấu hình AI thành công: Provider={provider}, Model={ai_config.model_name} bởi user {request.user.id}")
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Cập nhật cấu hình Trợ lý AI thành công! 🚀'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error', 
            'message': 'Dữ liệu JSON không hợp lệ!'
        }, status=400)
    except Exception as e:
        logger.error(f"Lỗi hệ thống khi cập nhật AI config cho nhóm {group_id}: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': 'Đã xảy ra lỗi hệ thống nội bộ!'
        }, status=500)

@login_required
@require_POST
def validate_and_test_ai_model(request, group_id):
    """
    Mục đích: Kiểm tra tính hợp lệ và khả năng phản hồi của Model/Provider trước khi lưu.
    Tại sao: Tránh việc lưu các model name ma (không tồn tại) hoặc API Key lỗi.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    if not Membership.objects.filter(group=group, user=request.user, role__in=['owner', 'admin']).exists():
        return JsonResponse({'status': 'error', 'message': 'Không có quyền thực thi!'}, status=403)

    try:
        data = json.loads(request.body)
        provider = data.get('ai_provider', '').strip().lower()
        model_name = data.get('ai_model', '').strip()
        api_key = data.get('custom_api_key', '').strip()

        # Thực hiện ping kiểm tra nhanh tùy thuộc vào Provider
        if provider == 'ollama':
            # Kiểm tra Ollama local server (mặc định port 11434)
            ollama_host = data.get('ollama_host', 'http://localhost:11434')
            response = requests.get(f"{ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]
                if model_name and model_name not in models:
                    return JsonResponse({
                        'status': 'error', 
                        'message': f"Model '{model_name}' không tồn tại trên Ollama server của bạn! Các model khả dụng: {', '.join(models)}"
                    }, status=400)
            else:
                return JsonResponse({'status': 'error', 'message': 'Không thể kết nối đến Ollama server!'}, status=400)

        elif provider == 'groq':
            if not api_key:
                return JsonResponse({'status': 'error', 'message': 'Cần cung cấp Groq API Key để kiểm tra!'}, status=400)
            # Test gọi thử API Groq lấy danh sách model hoặc ping nhẹ
            headers = {"Authorization": f"Bearer {api_key}"}
            res = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
            if res.status_code != 200:
                return JsonResponse({'status': 'error', 'message': 'Groq API Key không hợp lệ hoặc hết hạn!'}, status=400)

        # Trả về tín hiệu thành công để frontend tiến hành save chính thức
        return JsonResponse({
            'status': 'success',
            'message': f"Xác thực thành công model {model_name} cho {provider}! 🚀"
        })

    except requests.exceptions.RequestException as e:
        return JsonResponse({'status': 'error', 'message': f"Lỗi kết nối mạng tới Provider: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"Lỗi validate AI model: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Lỗi hệ thống trong quá trình kiểm tra model!'}, status=500)