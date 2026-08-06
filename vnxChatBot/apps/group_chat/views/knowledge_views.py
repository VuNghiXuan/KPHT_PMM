
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
from django.template.loader import render_to_string
from apps.ai_assistant.vector_store import VectorDBManager as vector_service
from apps.ai_assistant.file_processor import FileProcessor

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
        Trả về JSON chứa đoạn HTML render sẵn từ partial message_item.html để client append trực tiếp.

    Module liên kết: 
        - apps.group_chat.models (ChatGroup, Document, Message, Membership)
        - apps.group_chat.templates.group_chat.partials.message_item.html

    Logic giải thích (Why):
        - Việc trả về `rendered_html` giúp đồng bộ giao diện tuyệt đối giữa việc nhắn tin văn bản thông thường 
          và nhắn tin đính kèm file, kích hoạt ngay lập tức các nút tương tác (Tải xuống, Học 🧠, Feedback).
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
                document=document  # Liên kết trực tiếp tin nhắn với Document
            )

        # 4. Render trực tiếp message_item.html thành chuỗi HTML để trả về cho Client append vào DOM
        html_content = render_to_string(
            'group_chat/partials/message_item.html',
            {
                'message': message_obj,
                'request': request
            }
        )

        return JsonResponse({
            'status': 'success', 
            'message': 'Upload file thành công và đã đồng bộ lên dòng chat!',
            'document_id': document.id,
            'message_id': message_obj.id,
            'html': html_content  # 🚀 Gửi kèm HTML fragment xuống client
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
def knowledge_action_view(request, group_id, knowledge_id, action):
    """
    Function: knowledge_action_view
    Description:
        Thực hiện hành động trong Vòng đời tri thức (Knowledge Lifecycle): 
        Phê duyệt (approve) hoặc rollback (thu hồi) đối với KnowledgeUnit theo group_id.
    """
    # 1. Lấy KnowledgeUnit và đảm bảo thuộc đúng group_id (Tenant Isolation)
    ku = get_object_or_404(KnowledgeUnit, id=knowledge_id, document__group_id=group_id)
    
    # 2. Kiểm tra quyền thành viên trong nhóm
    membership = Membership.objects.filter(group_id=group_id, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thực hiện tác vụ này trong nhóm!'}, status=403)

    if action == 'approve':
        ku.status = 'approved'
        ku.save()  # Signal sẽ tự động đồng bộ vào Vector DB
        logger.info(f"✅ KnowledgeUnit ID {knowledge_id} trong nhóm {group_id} đã được duyệt (approved).")
        return JsonResponse({'status': 'success', 'message': 'Đã duyệt tri thức và đồng bộ vào Vector DB!'})
        
    elif action == 'rollback':
        ku.status = 'rollback'
        ku.save()  # Signal sẽ tự động dọn dẹp Vector Store
        logger.info(f"🔄 KnowledgeUnit ID {knowledge_id} trong nhóm {group_id} đã bị thu hồi (rollback).")
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

    

@login_required
@require_POST
def trigger_ai_learn_document_view(request, document_id):
    """
    Kích hoạt tiến trình đưa tài liệu vào kho tri thức RAG của nhóm.
    - Bước 1: Kiểm tra quyền hạn thành viên trong nhóm chứa tài liệu[cite: 1].
    - Bước 2: Cập nhật trạng thái KnowledgeUnit hoặc tạo mới nếu chưa có[cite: 1].
    - Bước 3: Đưa nội dung vào VectorDB thông qua VectorDBManager[cite: 1].
    - Bước 4: Kích hoạt tiến trình đưa tài liệu vào kho tri thức RAG của nhóm.
    """
    
    document = get_object_or_404(Document, id=document_id)
    group = document.group

    # Kiểm tra xem user hiện tại có thuộc nhóm này hay không (Tenant Isolation)[cite: 1]
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Bạn không có quyền thao tác trên tài liệu của nhóm này.'
        }, status=403)

    try:
        logger.info(f"🧠 [AILearn] Đang xử lý học tài liệu ID: {document.id} cho Group ID: {group.id}")

        # Trích xuất nội dung văn bản từ tệp vật lý của Document bằng FileProcessor
        extracted_content = ""
        if document.file:
            try:
                extracted_content = FileProcessor.extract_text_from_file(document.file.path)
            except Exception as parse_err:
                logger.warning(f"⚠️ Không thể parse file trực tiếp, dùng tên file: {parse_err}")
                extracted_content = f"Tài liệu: {document.file.name}"

        # Lấy hoặc tạo KnowledgeUnit tương ứng với Document[cite: 1]
        knowledge_unit, created = KnowledgeUnit.objects.get_or_create(
            document=document,
            defaults={
                'group': group,
                'status': 'pending',
                'content': extracted_content or f"Tài liệu: {document.file.name}"
            }
        )
        
        # Nếu KnowledgeUnit đã tồn tại nhưng chưa có nội dung, cập nhật lại
        if not created and not knowledge_unit.content:
            knowledge_unit.content = extracted_content
            knowledge_unit.save()

        # Tiến hành nạp vào Vector Store (ChromaDB)[cite: 1]
        vector_service.insert(
            group_id=group.id,
            text=knowledge_unit.content,
            doc_id=knowledge_unit.id
        )

        # Cập nhật trạng thái tri thức thành đã duyệt/đang hoạt động[cite: 1]
        knowledge_unit.status = 'approved'
        knowledge_unit.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Tài liệu đã được AI tiếp thu và đưa vào kho tri thức thành công!',
            'knowledge_id': knowledge_unit.id
        })

    except Exception as e:
        logger.error(f"❌ [AILearn Error] Lỗi khi AI học tài liệu ID {document_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Lỗi hệ thống khi xử lý vector: {str(e)}'
        }, status=500)