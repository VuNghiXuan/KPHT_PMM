# # File: apps/group_chat/views/knowledge_views.py

# """
# File: apps/group_chat/views/knowledge_views.py
# Mục đích: Quản lý vòng đời tri thức (Knowledge Lifecycle), upload tài liệu và phê duyệt RAG.
# Module liên kết: group_chat.models, ai_assistant.engine
# """

# import logging
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.views.decorators.http import require_POST
# from django.http import JsonResponse
# from django.db import transaction  # Đảm bảo tính toàn vẹn dữ liệu
# from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit, Message

# from django.contrib.auth import get_user_model

# User = get_user_model()
# # Khởi tạo logger để theo dõi debug
# logger = logging.getLogger(__name__)


# @login_required
# @require_POST
# def upload_document(request, group_id):
#     """
#     Function: upload_document
#     Description: 
#         Nhận file tải lên từ giao diện chat, lưu trữ vào thư mục riêng của ChatGroup Tenant, 
#         tạo bản ghi Document và tự động sinh một bản ghi Message đại diện trong phòng chat.
#         Signal post_save sẽ tự động kích hoạt tiến trình trích xuất RAG ngầm.

#     Module liên kết: 
#         - apps.group_chat.models (ChatGroup, Document, Message, Membership)

#     Giải thích logic (Why):
#         - Đảm bảo tính Group-Centric (tenant-based isolation): Mọi file và tin nhắn phát sinh 
#           đều phải ràng buộc chính xác với group_id.
#         - Tự động tạo Message đi kèm giúp người dùng thấy ngay file xuất hiện trên dòng thời gian chat, 
#           hỗ trợ tương tác tải về local hoặc gọi AI phân tích/học trực tiếp.
#     """
#     group = get_object_or_404(ChatGroup, id=group_id)
    
#     # 1. Kiểm tra quyền thành viên trong nhóm trước khi cho phép upload
#     membership = Membership.objects.filter(group=group, user=request.user).first()
#     if not membership:
#         return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền upload tài liệu trong nhóm này!'}, status=403)

#     if not request.FILES.get('file'):
#         return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tệp tin tải lên.'}, status=400)

#     uploaded_file = request.FILES['file']
    
#     try:
#         # Sử dụng transaction.atomic để đảm bảo tính toàn vẹn dữ liệu giữa Document và Message
#         with transaction.atomic():
#             # 2. Tạo bản ghi Document lưu trữ file gốc
#             document = Document.objects.create(
#                 group=group,
#                 file=uploaded_file,
#                 uploaded_by=request.user,
#                 upload_type='chat'
#             )
            
#             # 3. Tự động tạo một Message thông báo đính kèm file trong nhóm chat
#             file_name = uploaded_file.name
#             Message.objects.create(
#                 group=group,
#                 sender=membership,
#                 content=f"Đã đính kèm tài liệu mới: {file_name}",
#                 document=document  # Liên kết trực tiếp tin nhắn với Document để hiển thị card UI
#             )

#         return JsonResponse({
#             'status': 'success', 
#             'message': 'Upload file thành công và đã đồng bộ lên dòng chat!',
#             'document_id': document.id,
#             'file_name': file_name
#         })
        
#     except Exception as e:
#         logger.error(f"Lỗi hệ thống khi upload document cho group_id={group_id}: {str(e)}")
#         return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)
    
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

# File: apps/group_chat/views/knowledge_views.py

"""
File: apps/group_chat/views/knowledge_views.py
Mục đích: Quản lý vòng đời tri thức (Knowledge Lifecycle), upload tài liệu và phê duyệt RAG 
          theo mô hình Group-Centric (tenant-based isolation).
Module liên kết: group_chat.models, ai_assistant.engine
Tác giả: Kỹ sư hệ thống vnxChatBot
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction  # Đảm bảo tính toàn vẹn dữ liệu
from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit, Message
from django.contrib.auth import get_user_model

User = get_user_model()

# Khởi tạo logger để theo dõi debug và tracing hệ thống
logger = logging.getLogger(__name__)


@login_required
@require_POST
def upload_document(request, group_id):
    """
    Function: upload_document
    Description: 
        Nhận file tải lên từ giao diện chat, lưu trữ vào thư mục riêng của ChatGroup Tenant, 
        tạo bản ghi Document và tự động sinh một bản ghi Message đại diện trong phòng chat.
        Signal post_save sẽ tự động kích hoạt tiến trình trích xuất RAG ngầm.

    Module liên kết: 
        - apps.group_chat.models (ChatGroup, Document, Message, Membership)

    Giải thích logic (Why):
        - Đảm bảo tính Group-Centric (tenant-based isolation): Mọi file và tin nhắn phát sinh 
          đều phải ràng buộc chính xác với group_id.
        - Tự động tạo Message đi kèm giúp người dùng thấy ngay file xuất hiện trên dòng thời gian chat, 
          hỗ trợ tương tác tải về local hoặc gọi AI phân tích/học trực tiếp.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # 1. Kiểm tra quyền thành viên trong nhóm trước khi cho phép upload
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền upload tài liệu trong nhóm này!'}, status=403)

    if not request.FILES.get('file'):
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tệp tin tải lên.'}, status=400)

    uploaded_file = request.FILES['file']
    
    try:
        # Sử dụng transaction.atomic để đảm bảo tính toàn vẹn dữ liệu tuyệt đối giữa Document và Message
        with transaction.atomic():
            # 2. Tạo bản ghi Document lưu trữ file gốc
            document = Document.objects.create(
                group=group,
                file=uploaded_file,
                uploaded_by=request.user,
                upload_type='chat'
            )
            
            # 3. Tự động tạo một Message thông báo đính kèm file trong nhóm chat
            file_name = uploaded_file.name
            message_obj = Message.objects.create(
                group=group,
                sender=membership,
                content=f"📁 Đã đính kèm tài liệu mới: {file_name}",
                document=document  # Liên kết trực tiếp tin nhắn với Document để hiển thị card UI trên giao diện
            )

        return JsonResponse({
            'status': 'success', 
            'message': 'Upload file thành công và đã đồng bộ lên dòng chat!',
            'document_id': document.id,
            'message_id': message_obj.id,
            'file_name': file_name,
            'file_url': document.file.url if document.file else ''
        })
        
    except Exception as e:
        logger.error(f"❌ Lỗi hệ thống khi upload document cho group_id={group_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)


@login_required
def knowledge_management(request, group_id):
    """
    Function: knowledge_management
    Description:
        View quản lý kho tri thức (Knowledge Base) của nhóm.
        Cho phép thành viên xem danh sách tài liệu và các đơn vị tri thức (KnowledgeUnit) 
        để thực hiện kiểm duyệt (approve) hoặc từ chối/rollback.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # Lọc danh sách KnowledgeUnit theo quan hệ thông qua Document gắn với nhóm hiện tại
    knowledge_units = KnowledgeUnit.objects.filter(document__group=group).select_related('document', 'document__uploaded_by')
    
    # Lấy danh sách tài liệu đã upload của nhóm
    documents = Document.objects.filter(group=group).select_related('uploaded_by')

    context = {
        'group': group,
        'knowledge_units': knowledge_units,
        'documents': documents,
    }
    
    return render(request, 'group_chat/knowledge_management.html', context)


@login_required
@require_POST
def knowledge_action_view(request, knowledge_id, action):
    """
    Function: knowledge_action_view
    Description:
        Thực hiện hành động trong Vòng đời tri thức (Knowledge Lifecycle): 
        Phê duyệt (approve) hoặc rollback (thu hồi) đối với KnowledgeUnit.
    """
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id)
    
    # Kiểm tra quyền bảo mật tenant qua nhóm chứa document của KnowledgeUnit
    group = ku.document.group if ku.document else getattr(ku, 'group', None)
    if group:
        membership = Membership.objects.filter(group=group, user=request.user).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thực hiện tác vụ này trong nhóm!'}, status=403)

    if action == 'approve':
        ku.status = 'approved'
        ku.save() 
        logger.info(f"✅ KnowledgeUnit ID {knowledge_id} đã được duyệt (approved).")
        return JsonResponse({'status': 'success', 'message': 'Đã duyệt tri thức và đồng bộ vào Vector DB!'})
        
    elif action == 'rollback':
        ku.status = 'rollback'
        ku.save() 
        logger.info(f"🔄 KnowledgeUnit ID {knowledge_id} đã bị thu hồi (rollback).")
        return JsonResponse({'status': 'success', 'message': 'Đã rollback tri thức và xóa khỏi Vector DB!'})
        
    return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ!'}, status=400)


@login_required
@require_POST
def promote_knowledge_view(request, message_id):
    """
    Function: promote_knowledge_view
    Description: 
        Chuyển đổi một tin nhắn hội thoại thành đơn vị tri thức (KnowledgeUnit) 
        hoặc đẩy trạng thái tri thức vào chu trình chờ duyệt (Knowledge Lifecycle).
    
    Giải thích logic (Why):
    - Đảm bảo gán đầy đủ trường group và document cho KnowledgeUnit, tuân thủ tuyệt đối
      ràng buộc Group-Centric (tenant-based isolation) để tránh lỗi NOT NULL constraint.
    """
    try:
        message = get_object_or_404(Message, id=message_id)
        
        # 1. Kiểm tra quyền thành viên trong nhóm (Tenant Isolation)
        membership = Membership.objects.filter(group=message.group, user=request.user).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền trong nhóm này'}, status=403)

        # 2. Xác định chính xác User instance để gán vào uploaded_by
        uploader_user = request.user
        if message.sender and hasattr(message.sender, 'user'):
            uploader_user = message.sender.user

        # 3. Lấy hoặc tạo Document đại diện cho nhóm (nếu message có đính kèm document thì ưu tiên dùng luôn)
        document = message.document
        if not document:
            document, _ = Document.objects.get_or_create(
                group=message.group,
                defaults={'uploaded_by': uploader_user, 'upload_type': 'chat'}
            )
        
        # 4. Tạo hoặc cập nhật đơn vị tri thức KnowledgeUnit gắn chặt với group_id
        with transaction.atomic():
            knowledge_unit, created = KnowledgeUnit.objects.get_or_create(
                document=document,
                content=message.content,
                defaults={
                    'group': message.group,  # 👈 Bổ sung trực tiếp group để thỏa mãn ràng buộc dữ liệu
                    'status': 'pending'      # Trạng thái chờ duyệt theo chuẩn Knowledge Lifecycle
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
        logger.error(f"❌ Lỗi khi promote knowledge cho message_id={message_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)
    
    
@login_required
@require_POST
def rollback_knowledge(request, unit_id):
    """
    Function: rollback_knowledge
    Description:
        Hành động Rollback: Chuyển trạng thái KnowledgeUnit -> Rollback và xóa sạch vector khỏi VectorDB.
        Mục đích: Duy trì sự sạch sẽ của Vector Database theo chuẩn Knowledge Lifecycle.
    """
    unit = get_object_or_404(KnowledgeUnit, id=unit_id)
    
    # Xác định nhóm chat liên kết an toàn
    group = unit.document.group if unit.document else getattr(unit, 'group', None)
    if not group:
        return JsonResponse({"error": "Không tìm thấy thông tin nhóm liên kết của tri thức này."}, status=400)

    # Kiểm tra quyền Admin nhóm
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership or getattr(membership, 'role', 'member') != 'admin':
        return JsonResponse({"error": "Bạn không có quyền quản trị để thực hiện tác vụ này!"}, status=403)

    try:
        with transaction.atomic():
            unit.status = 'rollback'
            unit.save() 
        
        logger.info(f"🔄 Đã thực hiện rollback thành công cho KnowledgeUnit ID {unit_id}")
        return redirect('group_chat:knowledge_management', group_id=group.id)
        
    except Exception as e:
        logger.error(f"❌ Lỗi hệ thống khi rollback knowledge unit {unit_id}: {str(e)}")
        return JsonResponse({"error": f"Lỗi hệ thống: {str(e)}"}, status=500)