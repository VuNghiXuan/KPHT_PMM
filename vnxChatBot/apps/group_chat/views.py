# """
# Mục đích: Xử lý logic nghiệp vụ cho nhóm chat, quản lý tài liệu, tri thức 
#              và các endpoint AJAX phục vụ giao diện Workstation.
# Tác giả: Kiến trúc sư VnxChatBot
# Module liên kết: apps.group_chat.models, apps.ai_assistant.services, apps.core.models
# """
# import json
# import logging
# import traceback  # 🔍 Thêm thư viện trace lỗi
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.views.decorators.http import require_POST
# from django.http import JsonResponse
# from django.db import transaction  # Đảm bảo tính toàn vẹn dữ liệu
# from .models import ChatGroup, Membership, Document, KnowledgeUnit, Message, MessageFeedback
# from .services.feedback_service import FeedbackService
# from apps.ai_assistant.models import GroupAIProvider
# from apps.core.models import User
# from apps.subscriptions.models import Subscription
# from django.contrib.auth import get_user_model

# User = get_user_model()
# # Khởi tạo logger để theo dõi debug
# logger = logging.getLogger(__name__)

# @login_required
# def create_group(request):
#     """
#     Function: create_group
#     Description: 
#         Xử lý yêu cầu tạo mới một nhóm làm việc (ChatGroup). 
#         Mỗi nhóm được xem như một thực thể cô lập (Tenant-based Isolation) theo mô hình Group-Centric.
#         Sau khi tạo thành công, hệ thống tự động gán user hiện tại làm Admin,
#         khởi tạo gói cước và điều hướng trực tiếp vào phòng chat chi tiết của nhóm.
#     Module liên kết: apps.group_chat.models, apps.group_chat.forms
#     """
#     if request.method == 'POST':
#         group_name = request.POST.get('name')
#         if group_name:
#             # 1. Khởi tạo ChatGroup mới
#             group = ChatGroup.objects.create(name=group_name)
            
#             # 2. Gán người tạo làm quản trị viên (Admin) của nhóm
#             Membership.objects.create(
#                 user=request.user,
#                 group=group,
#                 role='admin'
#             )
            
#             # 3. Điều hướng chính xác vào route 'group_detail' kèm theo tham số group_id
#             return redirect('group_chat:group_detail', group_id=group.id)
            
#     return render(request, 'group_chat/create.html')


# @login_required
# def upload_document(request, group_id):
#     """
#     Function: upload_document
#     Description: 
#         Nhận file tải lên từ giao diện chat, lưu trữ vào thư mục riêng của ChatGroup Tenant, 
#         tạo bản ghi Document. Signal post_save sẽ tự động kích hoạt tiến trình trích xuất RAG.
#     """
#     if request.method == 'POST' and request.FILES.get('file'):
#         group = get_object_or_404(ChatGroup, id=group_id)
#         uploaded_file = request.FILES['file']
        
#         try:
#             # và lược bỏ trường 'title' nếu Model Document không khai báo trường này.
#             document = Document.objects.create(
#                 group=group,             # Khớp với field 'group' trong ChatGroup
#                 file=uploaded_file,
#                 uploaded_by=request.user
#             )
#             return JsonResponse({
#                 'status': 'success', 
#                 'message': 'Upload file thành công. AI đang tiến hành xử lý tri thức!',
#                 'document_id': document.id
#             })
#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
#     return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file hoặc sai phương thức.'}, status=400)

# def knowledge_management(request, group_id):
#     """
#     View quản lý kho tri thức (Knowledge Base) của nhóm.
#     Cho phép Admin nhóm xem danh sách tài liệu và các đơn vị tri thức (KnowledgeUnit) 
#     để thực hiện duyệt (approve) hoặc từ chối/rollback.
#     """
#     # 1. Lấy thông tin nhóm hiện tại (Tenant isolation theo group_id)
#     group = get_object_or_404(ChatGroup, id=group_id)
    
#     # 2. Sửa lại câu lệnh query để tránh lỗi ValueError: 
#     # KnowledgeUnit liên kết với Document, Document mới liên kết với ChatGroup.
#     knowledge_units = KnowledgeUnit.objects.filter(document__group=group).select_related('document')
    
#     # 3. Lấy danh sách tài liệu đã upload của nhóm
#     documents = Document.objects.filter(group=group)

#     context = {
#         'group': group,
#         'knowledge_units': knowledge_units,
#         'documents': documents,
#     }
    
#     return render(request, 'group_chat/knowledge_management.html', context)


# @login_required
# def rollback_knowledge(request, unit_id):
#     """
#     Hành động Rollback: Chuyển trạng thái KnowledgeUnit -> Xóa khỏi VectorDB.
#     Mục đích: Duy trì sự sạch sẽ của Vector Database theo chuẩn Knowledge Lifecycle.
#     """
#     unit = get_object_or_404(KnowledgeUnit, id=unit_id)
#     group = unit.document.chat_group

#     if not Membership.objects.filter(group=group, user=request.user, role='admin').exists():
#         return JsonResponse({"error": "Không có quyền thực hiện tác vụ này"}, status=403)

#     if request.method == "POST":
#         try:
#             with transaction.atomic():
#                 unit.status = 'rollback'
#                 unit.save() 
#             return redirect('group_chat:knowledge_management', group_id=group.id)
#         except Exception as e:
#             return JsonResponse({"error": f"Lỗi hệ thống: {str(e)}"}, status=500)


# @login_required
# def group_chat_detail(request, group_id):
#     """
#     Function: group_chat_detail
#     Description: 
#         Hiển thị giao diện chat chính của nhóm. Nếu người dùng xóa hết nhóm 
#         hoặc không tìm thấy nhóm, hệ thống sẽ tự động điều hướng về trang 
#         tạo nhóm mới hoặc dashboard để tránh lỗi 404.
#     """
#     # 1. Kiểm tra xem user có thuộc nhóm nào không, nếu không có nhóm nào -> chuyển hướng tạo nhóm
#     user_groups = ChatGroup.objects.filter(memberships__user=request.user)
#     if not user_groups.exists():
#         return redirect('group_chat:create_group') # Hoặc điều hướng về trang 'dashboard'

#     # 2. Lấy thông tin nhóm an toàn, nếu group_id không tồn tại nhưng user có nhóm khác -> lấy nhóm đầu tiên của họ
#     group = ChatGroup.objects.filter(id=group_id).first()
#     if not group:
#         first_group = user_groups.first()
#         return redirect('group_detail', group_id=first_group.id)
    
#     # 3. Xác thực xem user hiện tại có phải là thành viên hợp lệ của nhóm này không
#     membership = Membership.objects.filter(group=group, user=request.user).first()
#     if not membership:
#         # Nếu không phải thành viên nhưng nhóm tồn tại, chuyển về nhóm hợp lệ đầu tiên
#         valid_group = user_groups.first()
#         if valid_group:
#             return redirect('group_detail', group_id=valid_group.id)
#         return redirect('group_chat:create_group')
    
#     # 4. Truy vấn tin nhắn và dữ liệu liên quan
#     messages = list(group.messages.select_related('sender').order_by('-created_at')[:50])
#     messages.reverse()
    
#     memberships = group.memberships.select_related('user', 'user__profile').all()
#     documents = group.documents.all().order_by('-uploaded_at')
#     knowledge_units = KnowledgeUnit.objects.filter(document__group=group).order_by('-id')

#     subscription = getattr(group, 'subscription', None)
#     ai_config = getattr(group, 'aiconfig', None)

#     context = {
#         'group': group,
#         'membership': membership,
#         'messages': messages,
#         'memberships': memberships,
#         'documents': documents,
#         'knowledge_units': knowledge_units,
#         'subscription': subscription,
#         'ai_config': ai_config,
#     }
    
#     return render(request, 'group_chat/group_detail.html', context)




# @login_required
# @require_POST
# def knowledge_feedback_view(request, message_id):
#     """
#     Mục đích: Xử lý thả cảm xúc (Like, Heart, Dislike) cho tin nhắn theo phong cách Zalo.
#     Module liên kết: apps.group_chat.models (Message, MessageFeedback)
    
#     Giải thích logic (Why):
#     - Đảm bảo tính năng Group-Centric: Kiểm tra user có thuộc quyền membership trong nhóm chứa tin nhắn hay không.
#     - Xử lý Toggle cảm xúc: Nếu user đã thả cùng loại cảm xúc thì hủy (delete), nếu khác loại thì cập nhật, nếu chưa có thì tạo mới gắn với user.
#     """
#     message = get_object_or_404(Message, id=message_id)    
    
#     # Kiểm tra quyền thành viên trong nhóm làm việc (Tenant Isolation)
#     membership = request.user.memberships.filter(group=message.group).first()
#     if not membership:
#         return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

#     try:
#         data = json.loads(request.body)
#         feedback_type = data.get('type')
#     except Exception:
#         return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ'}, status=400)

#     if feedback_type not in ['like', 'heart', 'dislike']:
#         return JsonResponse({'status': 'error', 'message': 'Loại cảm xúc không hợp lệ'}, status=400)

#     # Kiểm tra xem user đã thả cảm xúc trên tin nhắn này chưa (Model MessageFeedback liên kết qua user và group)
#     existing_feedback = MessageFeedback.objects.filter(message=message, user=request.user).first()
    
#     if existing_feedback:
#         if existing_feedback.type == feedback_type:
#             existing_feedback.delete()  # Click lần nữa để bỏ cảm xúc (Toggle off)
#         else:
#             existing_feedback.type = feedback_type
#             existing_feedback.save()    # Thay đổi loại cảm xúc
#     else:
#         # Tạo mới bản ghi feedback gắn kết trực tiếp với group và user theo chuẩn database schema
#         MessageFeedback.objects.create(
#             group=message.group,
#             message=message,
#             user=request.user,
#             type=feedback_type
#         )

#     # Chuẩn bị dữ liệu trả về cho Front-end cập nhật tức thời qua WebSocket / AJAX
#     all_feedbacks = message.feedbacks.select_related('user').all()
#     total_count = all_feedbacks.count()

#     # Gom nhóm các loại icon đang có hiển thị trên giao diện
#     feedback_details = []
#     icons_map = {'like': '👍', 'heart': '❤️', 'dislike': '👎'}
    
#     grouped_icons = list(all_feedbacks.values_list('type', flat=True).distinct())
#     rendered_icons = [icons_map[t] for t in grouped_icons if t in icons_map]

#     for fb in all_feedbacks:
#         feedback_details.append({
#             'username': fb.user.username if fb.user else "AI",
#             'type': fb.type,
#             'icon': icons_map.get(fb.type, '')
#         })

#     return JsonResponse({
#         'status': 'success',
#         'total_count': total_count,
#         'rendered_icons': rendered_icons,
#         'feedbacks': feedback_details
#     })


# @login_required
# def message_reactions_detail_view(request, message_id):
#     """
#     Mục đích: Trả về danh sách chi tiết các lượt tương tác (Like, Heart, Dislike) của tin nhắn.
#     Module liên kết: apps.group_chat.models (Message, MessageFeedback)
    
#     Giải thích logic (Why):
#     - Đã lược bỏ các ký tự đặc biệt/emoji khỏi câu lệnh logger để tương thích hoàn toàn 
#       với bảng mã CP1252 mặc định trên Windows Terminal, tránh lỗi UnicodeEncodeError rác.
#     - Truy vấn chuẩn xác các bản ghi MessageFeedback dựa trên message_id để hiển thị đúng 
#       số lượng và icon tương ứng lên modal giao diện.
#     """
#     logger.info(f"==> [DEBUG] Bat dau xu ly reactions-detail cho message_id={message_id} boi user='{request.user.username}'")
    
#     # 1. Lấy thông tin tin nhắn
#     message = get_object_or_404(Message, id=message_id)
#     logger.info(f"==> [DEBUG] Tim thay tin nhắn ID {message.id} thuoc ChatGroup ID {message.group.id}")

#     # 2. Kiểm tra quyền thành viên trong nhóm (Tenant Isolation)
#     membership = request.user.memberships.filter(group=message.group).first()
#     if not membership:
#         logger.warning(f"==> [WARN] User khong co quyền trong nhóm nay")
#         return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

#     # 3. Truy vấn toàn bộ feedback gắn với message này
#     feedbacks = MessageFeedback.objects.filter(message=message).select_related('user')
#     total_count = feedbacks.count()
#     logger.info(f"==> [DEBUG] Tong so luong feedbacks tim thay trong DB: {total_count}")

#     icons_map = {'like': '👍', 'heart': '❤️', 'dislike': '👎'}
#     feedback_details = []

#     for fb in feedbacks:
#         username = fb.user.username if fb.user else "AI"
#         icon = icons_map.get(fb.type, '')
#         # Lưu ý: Không đưa biến 'icon' vào logger để tránh lỗi mã hóa Windows console
#         logger.info(f"    + Feedback: User={username}, Type={fb.type}")
#         feedback_details.append({
#             'username': username,
#             'type': fb.type,
#             'icon': icon
#         })

#     response_data = {
#         'status': 'success',
#         'total_count': total_count,
#         'feedbacks': feedback_details
#     }
    
#     logger.info(f"==> [DEBUG] Tra ve du lieu thanh cong cho client.")
#     return JsonResponse(response_data)


# @login_required
# def update_ai_config_view(request, group_id):
#     """
#     Cập nhật cấu hình AI riêng cho nhóm (Group-Centric AI Configuration).
#     """
#     if request.method != 'POST':
#         return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)
        
#     group = get_object_or_404(ChatGroup, id=group_id)
#     try:
#         data = json.loads(request.body)
#         ai_config, created = GroupAIProvider.objects.get_or_create(group=group)
#         ai_config.provider = data.get('provider', 'gemini')
#         ai_config.temperature = float(data.get('temperature', 0.7))
#         ai_config.system_prompt = data.get('system_prompt', '')
#         ai_config.save()
        
#         return JsonResponse({'status': 'success', 'message': 'Cập nhật cấu hình AI thành công!'})
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# @login_required
# def knowledge_action_view(request, knowledge_id, action):
#     """
#     Thực hiện phê duyệt (approve) hoặc rollback (vòng đời tri thức) đối với KnowledgeUnit.
#     """
#     if request.method != 'POST':
#         return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)
        
#     ku = get_object_or_404(KnowledgeUnit, id=knowledge_id)
    
#     if action == 'approve':
#         ku.status = 'approved'
#         ku.save() 
#         return JsonResponse({'status': 'success', 'message': 'Đã duyệt tri thức và đồng bộ vào Vector DB!'})
#     elif action == 'rollback':
#         ku.status = 'rollback'
#         ku.save() 
#         return JsonResponse({'status': 'success', 'message': 'Đã rollback tri thức và xóa khỏi Vector DB!'})
        
#     return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ!'}, status=400)

# @login_required
# @require_POST
# def add_member_to_group(request, group_id):
#     """
#     Function: add_member_to_group
#     Description: 
#         Xử lý yêu cầu thêm thành viên mới vào nhóm làm việc (ChatGroup) thông qua chuẩn JSON API.
#         Hàm này gộp chung logic kiểm tra quyền quản trị (owner/admin), tìm kiếm linh hoạt 
#         qua username hoặc email, kiểm tra giới hạn gói cước (Subscription), và đảm bảo 
#         luôn trả về định dạng JSON an toàn cho phía client.
    
#     Module liên kết: apps.group_chat.models, apps.subscriptions.models
#     """
#     # 1. Lấy thông tin nhóm theo cơ chế Tenant-based Isolation
#     group = get_object_or_404(ChatGroup, id=group_id)
    
#     # 2. Kiểm tra quyền quản trị qua Membership (Chỉ owner hoặc admin mới được thêm thành viên)
#     is_admin = Membership.objects.filter(
#         group=group, 
#         user=request.user, 
#         role__in=['owner', 'admin']
#     ).exists()
    
#     if not is_admin:
#         return JsonResponse({
#             'status': 'error', 
#             'message': 'Bạn không có quyền quản trị để thêm thành viên vào nhóm này!'
#         }, status=403)

#     try:
#         # 3. Phân tích dữ liệu JSON từ request body
#         data = json.loads(request.body)
#         identifier = data.get('username') or data.get('email')
#         role = data.get('role', 'member') # Mặc định là thành viên thông thường
        
#         if not identifier:
#             return JsonResponse({
#                 'status': 'error', 
#                 'message': 'Vui lòng cung cấp username hoặc email của thành viên cần thêm!'
#             }, status=400)
        
#         # 4. Tìm kiếm user linh hoạt bằng cả username hoặc email
#         user_to_add = User.objects.filter(username=identifier).first() or User.objects.filter(email=identifier).first()
        
#         if not user_to_add:
#             return JsonResponse({
#                 'status': 'error', 
#                 'message': f'Không tìm thấy người dùng với thông tin: {identifier}'
#             }, status=404)
            
#         # 5. Kiểm tra xem người dùng đã là thành viên của nhóm hay chưa
#         if Membership.objects.filter(group=group, user=user_to_add).exists():
#             return JsonResponse({
#                 'status': 'error', 
#                 'message': 'Người dùng này đã là thành viên của nhóm!'
#             }, status=400)
            
#         # 6. Kiểm tra giới hạn gói cước Subscription (Group-Centric)
#         subscription, _ = Subscription.objects.get_or_create(group=group)
#         current_members_count = Membership.objects.filter(group=group).count()
#         max_allowed_members = getattr(subscription, 'max_members', getattr(subscription, 'max_users', 6))
        
#         if current_members_count >= max_allowed_members:
#             return JsonResponse({
#                 'status': 'error', 
#                 'message': f'Nhóm đã đạt giới hạn tối đa ({max_allowed_members} thành viên) theo gói cước hiện tại!'
#             }, status=400)
            
#         # 7. Tạo bản ghi Membership mới cho thành viên
#         Membership.objects.create(group=group, user=user_to_add, role=role)
        
#         return JsonResponse({
#             'status': 'success', 
#             'message': f'Đã thêm thành viên {user_to_add.username} vào nhóm thành công!'
#         })
        
#     except json.JSONDecodeError:
#         return JsonResponse({
#             'status': 'error', 
#             'message': 'Dữ liệu gửi lên không đúng định dạng JSON chuẩn.'
#         }, status=400)
#     except Exception as e:
#         return JsonResponse({
#             'status': 'error', 
#             'message': f'Lỗi hệ thống nội bộ: {str(e)}'
#         }, status=500)

# @login_required
# def get_group_members_api(request, group_id):
#     """
#     API trả về danh sách thành viên và AI trong nhóm dưới dạng JSON
#     phục vụ tính năng gán thẻ (@mention) trên giao diện chat.
#     """
#     try:
#         chat_group = ChatGroup.objects.get(id=group_id)
#         # Kiểm tra quyền thành viên (Tenant Isolation theo ChatGroup)
#         if not Membership.objects.filter(group=chat_group, user=request.user).exists():
#             return JsonResponse({'status': 'error', 'message': 'Không có quyền truy cập'}, status=403)
        
#         memberships = Membership.objects.filter(group=chat_group).select_related('user__profile')
        
#         members_data = []
#         for m in memberships:
#             if m.is_ai:
#                 members_data.append({
#                     'id': 'ai',
#                     'name': 'AI Assistant',
#                     'username': 'ai',
#                     'is_ai': True,
#                     'avatar': '🤖'
#                 })
#             elif m.user:
#                 avatar_url = m.user.profile.avatar.url if hasattr(m.user, 'profile') and m.user.profile.avatar else None
#                 members_data.append({
#                     'id': m.user.id,
#                     'name': m.user.get_full_name() or m.user.username,
#                     'username': m.user.username,
#                     'is_ai': False,
#                     'avatar': avatar_url
#                 })
                
#         return JsonResponse({'status': 'success', 'members': members_data})
#     except ChatGroup.DoesNotExist:
#         return JsonResponse({'status': 'error', 'message': 'Nhóm không tồn tại'}, status=404)



# @login_required
# def handle_message_feedback_ajax(request, message_id):
#     """
#     Xử lý thả cảm xúc (Like, Heart, Dislike) cho tin nhắn qua AJAX.
    
#     Logic nghiệp vụ:
#         - Kiểm tra thành viên thuộc nhóm (Tenant Isolation).
#         - Toggle cảm xúc: Nếu đã tồn tại -> Xóa (Hủy thả), nếu chưa -> Tạo mới.
#         - Trả về tổng số lượng chi tiết để client cập nhật giao diện trực quan.
#     """
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             feedback_type = data.get('type') # Các giá trị hỗ trợ: 'like', 'heart', 'dislike'
            
#             valid_feedback_types = ['like', 'heart', 'dislike']
#             if feedback_type not in valid_feedback_types:
#                 return JsonResponse({'status': 'error', 'message': 'Loại tương tác không hợp lệ.'}, status=400)
            
#             message = Message.objects.get(id=message_id)
            
#             # Kiểm tra Membership của user trong nhóm chứa tin nhắn (Group-Centric)
#             membership = Membership.objects.filter(user=request.user, group=message.group).first()
#             if not membership:
#                 return JsonResponse({'status': 'error', 'message': 'Bạn không phải thành viên của nhóm này.'}, status=403)
            
#             # Kiểm tra xem user đã thả cảm xúc này chưa
#             existing_feedback = MessageFeedback.objects.filter(
#                 message=message, 
#                 member=membership, 
#                 feedback_type=feedback_type
#             ).first()
            
#             if existing_feedback:
#                 existing_feedback.delete()
#                 action = 'removed'
#             else:
#                 MessageFeedback.objects.create(
#                     message=message,
#                     member=membership,
#                     feedback_type=feedback_type
#                 )
#                 action = 'added'
                
#             # Thống kê số lượng chi tiết cho từng loại cảm xúc
#             reactions_count = {
#                 'like': message.feedbacks.filter(feedback_type='like').count(),
#                 'heart': message.feedbacks.filter(feedback_type='heart').count(),
#                 'dislike': message.feedbacks.filter(feedback_type='dislike').count(),
#             }
#             total_count = message.feedbacks.count()
            
#             return JsonResponse({
#                 'status': 'success',
#                 'action': action,
#                 'reactions_count': reactions_count,
#                 'total_count': total_count,
#             })
            
#         except Message.DoesNotExist:
#             return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tin nhắn.'}, status=404)
#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
#     return JsonResponse({'status': 'error', 'message': 'Phương thức không được hỗ trợ.'}, status=405)


# @login_required
# @require_POST
# def promote_knowledge_view(request, message_id):
#     """
#     Mục đích: Chuyển đổi một tin nhắn hội thoại thành đơn vị tri thức (KnowledgeUnit) 
#     hoặc đẩy trạng thái tri thức vào chu trình duyệt (Knowledge Lifecycle).
    
#     Module liên kết: apps.group_chat.models (Message, KnowledgeUnit, Document)
    
#     Giải thích logic (Why):
#     - Đảm bảo gán đầy đủ trường group và document cho KnowledgeUnit, tuân thủ tuyệt đối
#       ràng buộc Group-Centric (tenant-based isolation) để tránh lỗi NOT NULL constraint.
#     """
#     try:
#         message = get_object_or_404(Message, id=message_id)
        
#         # 1. Kiểm tra quyền thành viên trong nhóm (Tenant Isolation)
#         membership = request.user.memberships.filter(group=message.group).first()
#         if not membership:
#             return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

#         # 2. Xác định chính xác User instance để gán vào uploaded_by
#         uploader_user = request.user
#         if message.sender:
#             if hasattr(message.sender, 'user'):  # Trường hợp sender là Membership
#                 uploader_user = message.sender.user
#             elif isinstance(message.sender, User):  # Trường hợp sender là User trực tiếp
#                 uploader_user = message.sender

#         # 3. Tạo hoặc lấy Document tương ứng của nhóm
#         document, _ = Document.objects.get_or_create(
#             group=message.group,
#             defaults={'uploaded_by': uploader_user}
#         )
        
#         # 4. Tạo hoặc cập nhật đơn vị tri thức KnowledgeUnit gắn chặt với group_id
#         knowledge_unit, created = KnowledgeUnit.objects.get_or_create(
#             document=document,
#             group=message.group,  # 👈 Bổ sung trực tiếp group để thỏa mãn ràng buộc NOT NULL
#             content=message.content,
#             defaults={
#                 'status': 'pending'  # Chờ duyệt theo Knowledge Lifecycle
#             }
#         )
        
#         if not created and knowledge_unit.status == 'rollback':
#             knowledge_unit.status = 'pending'
#             knowledge_unit.content = message.content
#             knowledge_unit.save()

#         return JsonResponse({
#             'status': 'success',
#             'message': 'Đã chuyển tin nhắn vào kho tri thức chờ duyệt thành công!',
#             'knowledge_id': knowledge_unit.id
#         })
        
#     except Exception as e:
#         logger.error(f"Lỗi khi promote knowledge cho message_id={message_id}: {str(e)}")
#         return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)