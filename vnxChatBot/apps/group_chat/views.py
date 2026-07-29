"""
Mục đích: Xử lý logic nghiệp vụ cho nhóm chat, quản lý tài liệu, tri thức 
             và các endpoint AJAX phục vụ giao diện Workstation.
Tác giả: Kiến trúc sư VnxChatBot
Module liên kết: apps.group_chat.models, apps.ai_assistant.services, apps.core.models
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction  # Đảm bảo tính toàn vẹn dữ liệu
from .models import ChatGroup, Membership, Document, KnowledgeUnit, Message
from .services.feedback_service import FeedbackService
from apps.ai_assistant.models import GroupAIProvider
from apps.core.models import User
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
            
            # 3. Điều hướng chính xác vào route 'chat_detail' kèm theo tham số group_id
            return redirect('group_chat:chat_detail', group_id=group.id)
            
    return render(request, 'group_chat/create.html')


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


@login_required
def group_chat_detail(request, group_id):
    """
    Function: group_chat_detail
    Description: 
        Hiển thị giao diện chat chính và không gian quản trị của nhóm làm việc, 
        tích hợp WebSocket, danh sách tài liệu tri thức, thành viên và cấu hình AI. 
        Đảm bảo kiểm tra tính cô lập dữ liệu (Tenant Isolation) dựa trên group_id 
        và xác thực quyền thành viên trước khi ném dữ liệu vào template context.
    """
    # 1. Kiểm tra và lấy thông tin nhóm dựa trên group_id (Tenant isolation cốt lõi)
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # 2. Xác thực xem user hiện tại có phải là thành viên hợp lệ của nhóm này không
    membership = get_object_or_404(Membership, group=group, user=request.user)
    
    # 3. Truy vấn 50 tin nhắn mới nhất và đảo ngược lại thứ tự hiển thị
    messages = list(group.messages.select_related('sender').order_by('-created_at')[:50])
    messages.reverse()
    
    # 4. Tối ưu truy vấn danh sách thành viên
    memberships = group.memberships.select_related('user', 'user__profile').all()

    # 5. Lấy tài liệu và tri thức của nhóm (Khắc phục lỗi bằng cách dùng -id hoặc approved_at)
    documents = group.documents.all().order_by('-uploaded_at')
    knowledge_units = KnowledgeUnit.objects.filter(document__group=group).order_by('-id')

    # 6. Lấy thông tin gói cước và cấu hình AI riêng của nhóm
    subscription = getattr(group, 'subscription', None)
    ai_config = getattr(group, 'aiconfig', None)

    # 7. Đóng gói toàn bộ biến ngữ cảnh (context) để truyền sang template
    context = {
        'group': group,
        'membership': membership,
        'messages': messages,
        'memberships': memberships,
        'documents': documents,
        'knowledge_units': knowledge_units,
        'subscription': subscription,
        'ai_config': ai_config,
    }
    
    return render(request, 'group_chat/chat_detail.html', context)

@login_required
def knowledge_feedback_view(request, message_id):
    """
    Function: knowledge_feedback_view
    Description: 
        API endpoint nhận yêu cầu POST chứa loại feedback (like/dislike), 
        gọi FeedbackService để ghi nhận vào Database phục vụ Fine-tuning Data.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_type = data.get('type') 
            comment = data.get('comment', '')
            
            if feedback_type not in ['like', 'dislike']:
                return JsonResponse({'status': 'error', 'message': 'Loại phản hồi không hợp lệ.'}, status=400)

            message = get_object_or_404(Message, id=message_id)
            group = message.group

            FeedbackService.record_feedback(
                group=group,
                message=message,
                user=request.user,
                feedback_type=feedback_type,
                comment=comment
            )
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Đã ghi nhận phản hồi của bạn. Cảm ơn bạn đã giúp tinh chỉnh AI!'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Chỉ chấp nhận phương thức POST.'}, status=405)


@login_required
def invite_member_view(request, group_id):
    """
    Mời thành viên mới vào nhóm dựa trên email và kiểm tra giới hạn gói cước subscriptions.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)
    
    group = get_object_or_404(ChatGroup, id=group_id)
    
    if not group.membership_set.filter(user=request.user, role='admin').exists() and request.user != group.admin:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền mời thành viên!'}, status=403)
        
    try:
        data = json.loads(request.body)
        email = data.get('email')
        user_to_add = User.objects.get(email=email)
        
        max_members = group.subscription.max_members if hasattr(group, 'subscription') else 6
        current_count = group.membership_set.count()
        
        if current_count >= max_members:
            return JsonResponse({'status': 'error', 'message': f'Đã đạt giới hạn tối đa {max_members} thành viên của gói cước!'}, status=400)
            
        if Membership.objects.filter(group=group, user=user_to_add).exists():
            return JsonResponse({'status': 'error', 'message': 'Người dùng đã là thành viên của nhóm!'}, status=400)
            
        Membership.objects.create(group=group, user=user_to_add, role='member')
        return JsonResponse({'status': 'success', 'message': f'Đã thêm {email} vào nhóm thành công!'})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy người dùng với email này!'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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

def add_member_to_group(request, group_id):
    """
    Xử lý logic thêm thành viên vào nhóm, tuân thủ giới hạn gói cước Subscription.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # Kiểm tra quyền Admin nhóm (hoặc Owner)
    is_admin = Membership.objects.filter(group=group, user=request.user, role__in=[Membership.Role.OWNER, Membership.Role.ADMIN]).exists()
    if not is_admin:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thêm thành viên vào nhóm này!'}, status=403)

    if request.method == 'POST':
        username = request.POST.get('username')
        role = request.POST.get('role', Membership.Role.MEMBER)
        
        try:
            user_to_add = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Không tìm thấy người dùng có username: {username}'}, status=404)
            
        # Kiểm tra xem đã là thành viên chưa
        if Membership.objects.filter(group=group, user=user_to_add).exists():
            return JsonResponse({'status': 'error', 'message': 'Người dùng này đã là thành viên của nhóm!'}, status=400)
            
        # Kiểm tra giới hạn gói cước Subscription (Ví dụ Free tối đa 6 thành viên kể cả AI)
        subscription, _ = Subscription.objects.get_or_create(group=group)
        current_members_count = Membership.objects.filter(group=group).count()
        
        if current_members_count >= subscription.max_members:
            return JsonResponse({'status': 'error', 'message': f'Nhóm đã đạt giới hạn tối đa ({subscription.max_members} thành viên) theo gói cước hiện tại!'}, status=400)
            
        # Thêm thành viên mới
        Membership.objects.create(group=group, user=user_to_add, role=role)
        return JsonResponse({'status': 'success', 'message': f'Đã thêm thành công {username} vào nhóm!'})
        
    return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ.'}, status=405)