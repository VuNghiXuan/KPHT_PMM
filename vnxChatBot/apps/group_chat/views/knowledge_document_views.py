"""
File: apps/group_chat/views/knowledge_document_views.py
Mục đích: Xử lý upload tài liệu, tích hợp file vào hệ thống và kích hoạt AI học tài liệu.
"""

import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.template.loader import render_to_string

from apps.group_chat.models import ChatGroup, Membership, Document, KnowledgeUnit, Message
from apps.ai_assistant.vector_store import VectorDBManager as vector_service
from apps.ai_assistant.services.document_processor import DocumentProcessorService as FileProcessor

logger = logging.getLogger(__name__)


@login_required
@require_POST
def upload_document(request, group_id):
    """
    Nhận file tải lên từ giao diện chat, lưu trữ vào thư mục riêng của ChatGroup Tenant, 
    tạo bản ghi Document và tự động sinh bản ghi Message đính kèm trong phòng chat.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    membership = Membership.objects.filter(group=group, user=request.user).first()
    if not membership:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền upload tài liệu trong nhóm này!'}, status=403)

    if not request.FILES.get('file'):
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy tệp tin tải lên.'}, status=400)

    uploaded_file = request.FILES['file']
    
    try:
        with transaction.atomic():
            document = Document.objects.create(
                group=group,
                file=uploaded_file,
                uploaded_by=request.user,
                upload_type='chat'
            )
            
            file_name = uploaded_file.name
            message_obj = Message.objects.create(
                group=group,
                sender=membership,
                content=f"📁 Đã đính kèm tài liệu mới: {file_name}",
                document=document
            )

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
            'html': html_content
        })
        
    except Exception as e:
        logger.error(f"❌ Lỗi hệ thống khi upload document cho group_id={group_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}, status=500)


@login_required
@require_POST
def delete_document_view(request, document_id):
    """
    Xóa tài liệu gốc, thu hồi tri thức liên quan và xóa tệp vật lý an toàn theo nhóm.
    """
    document = get_object_or_404(Document, id=document_id)
    group = document.group

    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xóa tài liệu này!'}, status=403)

    try:
        with transaction.atomic():
            if document.file:
                document.file.delete(save=False)
            document.delete()
        
        logger.info(f"🗑️ [Document] Đã xóa thành công tài liệu ID: {document_id} trong nhóm ID: {group.id}")
        return JsonResponse({'status': 'success', 'message': 'Xóa tài liệu thành công!'})
    except Exception as e:
        logger.error(f"❌ [Document Error] Lỗi khi xóa tài liệu ID {document_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống khi xóa: {str(e)}'}, status=500)

    
@login_required
@require_POST
def trigger_ai_learn_document_view(request, document_id):
    """
    🧠 Trích xuất tri thức từ tài liệu và đưa vào hàng đợi chờ duyệt (Pending).
    Tuân thủ quy tắc: Cấm tuyệt đối đẩy dữ liệu pending vào Vector Store.
    """
    document = get_object_or_404(Document, id=document_id)
    group = document.group

    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Bạn không có quyền thao tác trên tài liệu của nhóm này.'
        }, status=403)

    try:
        logger.info(f"📚 [AILearn] Đang trích xuất tài liệu ID: {document.id} cho Group ID: {group.id}")

        extracted_content = ""
        if document.file:
            try:
                extracted_content = FileProcessor.extract_text_from_file(document.file.path)
            except Exception as parse_err:
                logger.warning(f"⚠️ Không thể parse file trực tiếp, dùng tên file: {parse_err}")
                extracted_content = f"Tài liệu: {document.file.name}"

        # Tạo bản ghi KnowledgeUnit với trạng thái 'pending'
        knowledge_unit, created = KnowledgeUnit.objects.get_or_create(
            document=document,
            defaults={
                'group': group,
                'status': 'pending', 
                'content': extracted_content or f"Tài liệu: {document.file.name}"
            }
        )
        
        if not created:
            knowledge_unit.content = extracted_content or knowledge_unit.content
            knowledge_unit.status = 'pending'
            knowledge_unit.save()

        # 🛑 CHÚ Ý: Đã loại bỏ hoàn toàn vector_service.insert() tại đây 
        # để dữ liệu nằm chờ người quản trị duyệt trên knowledge_dashboard.html.

        return JsonResponse({
            'status': 'success',
            'message': 'Tài liệu đã được trích xuất và chuyển vào danh sách chờ duyệt!',
            'knowledge_id': knowledge_unit.id
        })

    except Exception as e:
        logger.error(f"❌ [AILearn Error] Lỗi khi trích xuất tài liệu ID {document_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Lỗi hệ thống khi trích xuất: {str(e)}'
        }, status=500)