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

from apps.group_chat.models import ChatGroup, Membership, Document, RawDocument, KnowledgeChapter, Message
from apps.ai_assistant.tasks import process_document_task
from apps.ai_assistant.vector_store import VectorDBManager as vector_service
from apps.ai_assistant.services.document_processor import DocumentProcessorService as FileProcessor
from django.db.models import Q

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
            'group_chat/partials/chat_ui/message_item.html',
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
    🧠 Trích xuất tri thức thô từ tài liệu và đưa vào bảng trung gian RawDocument (PENDING).
    Tuân thủ quy tắc: Cấm tuyệt đối đẩy dữ liệu pending/staging vào Vector Store.
    """
    document = get_object_or_404(Document, id=document_id)
    group = document.group

    # Kiểm tra quyền thành viên theo mô hình Group-Centric tuyệt đối
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

        content_to_save = extracted_content or f"Tài liệu: {document.file.name}"

        # 🛠️ Truy vấn an toàn: Lấy bản ghi mới nhất, tự động dọn dẹp các bản ghi trùng lặp thừa
        existing_raw_docs = RawDocument.objects.filter(document=document).order_by('-created_at')
        
        if existing_raw_docs.exists():
            raw_doc = existing_raw_docs.first()
            # Dọn dẹp sạch sẽ các bản ghi thừa trong database cũ để tránh lỗi phát sinh
            if existing_raw_docs.count() > 1:
                logger.warning(f"🧹 Đang dọn dẹp {existing_raw_docs.count() - 1} bản ghi RawDocument trùng lặp cho tài liệu ID {document.id}")
                existing_raw_docs.exclude(id=raw_doc.id).delete()
            
            # Cập nhật trạng thái chuẩn hóa ('PENDING') và nội dung mới
            raw_doc.group = group
            raw_doc.status = 'PENDING'
            raw_doc.raw_content = content_to_save
            raw_doc.save()
        else:
            raw_doc = RawDocument.objects.create(
                document=document,
                group=group,
                status='PENDING',
                raw_content=content_to_save
            )

        # 🛑 QUY TẮC VÀNG: Tuyệt đối không tương tác với Vector Store tại đây.
        return JsonResponse({
            'status': 'success',
            'message': 'Tài liệu đã được trích xuất vào phân vùng Staging chờ phân tích cấu trúc!',
            'raw_document_id': raw_doc.id
        })

    except Exception as e:
        logger.error(f"❌ [AILearn Error] Lỗi khi trích xuất tài liệu ID {document_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Lỗi hệ thống khi trích xuất: {str(e)}'
        }, status=500)


@login_required
def search_knowledge_view(request, group_id):
    """
    🔍 API tìm kiếm tri thức trong phạm vi nhóm (Group-Centric).
    - Kiểm tra quyền thành viên nhóm tuyệt đối.
    - Validate từ khóa: tối thiểu 10 ký tự và ít nhất 3 cụm từ (từ).
    - Chỉ tìm kiếm trên các chương tri thức đã được phê duyệt (KnowledgeChapter, status='approved').
    """
    group = get_object_or_404(ChatGroup, id=group_id)

    # 1. Kiểm tra quyền thành viên theo mô hình Group-Centric tuyệt đối
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Bạn không có quyền tìm kiếm tri thức trong nhóm này!'
        }, status=403)

    query = request.GET.get('q', '').strip()
    
    # 2. Xử lý khi chuỗi rỗng
    if not query:
        return JsonResponse({
            'status': 'success',
            'query': '',
            'count': 0,
            'results': []
        })

    # 3. Validation Logic: Kiểm tra độ dài và số lượng từ tối thiểu để tránh truy vấn rác
    words = query.split()
    if len(query) < 10 or len(words) < 3:
        return JsonResponse({
            "status": "error",
            "code": "invalid_search_query",
            "message": "Nội dung tìm kiếm chưa đủ ý nghĩa.",
            "details": {
                "min_characters": 10,
                "min_phrases": 3,
                "provided": {
                    "characters": len(query),
                    "phrases": len(words)
                }
            },
            "suggestions_list": [
                "Tra giá vàng hôm nay",
                "Hướng dẫn quy trình phê duyệt",
                "Chính sách bảo mật dữ liệu"
            ]
        }, status=400)

    try:
        # 4. Truy vấn KnowledgeChapter đã approved, lọc theo group_id và từ khóa (sử dụng summary)
        chapters = KnowledgeChapter.objects.filter(
            group_id=group.id,
            status='approved'
        ).filter(
            Q(title__icontains=query) | Q(summary__icontains=query)
        ).order_by('-version')[:20]  # Giới hạn tối đa 20 kết quả hàng đầu

        results = []
        for ch in chapters:
            results.append({
                'id': ch.id,
                'title': ch.title,
                'summary': ch.summary[:200] + '...' if ch.summary and len(ch.summary) > 200 else (ch.summary or ''),
                'confidence_score': 1.0,
                'updated_at': ch.updated_at.strftime('%Y-%m-%d %H:%M') if hasattr(ch, 'updated_at') and ch.updated_at else None
            })

        logger.info(f"🔎 [SearchKnowledge] Nhóm ID {group.id}: Tìm thấy {len(results)} kết quả cho từ khóa '{query}'")

        return JsonResponse({
            'status': 'success',
            'query': query,
            'count': len(results),
            'results': results
        })

    except Exception as e:
        logger.error(f"❌ [SearchKnowledge Error] Lỗi khi tìm kiếm tri thức nhóm {group_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Lỗi hệ thống khi tìm kiếm: {str(e)}'
        }, status=500)

@login_required
def raw_document_status_view(request, group_id, raw_doc_id):
    """
    📊 API kiểm tra trạng thái tiến trình xử lý của tài liệu thô (RawDocument) qua Celery.
    Đảm bảo cô lập tuyệt đối theo group_id và kiểm tra quyền thành viên nhóm.
    """
    group = get_object_or_404(ChatGroup, id=group_id)
    
    # Kiểm tra quyền thành viên nhóm (Group-Centric)
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({
            'status': 'error',
            'message': 'Bạn không có quyền truy cập dữ liệu của nhóm này!'
        }, status=403)

    # Truy vấn RawDocument với điều kiện cô lập group tuyệt đối
    raw_doc = get_object_or_404(RawDocument, id=raw_doc_id, group=group)

    return JsonResponse({
        'status': 'success',
        'data': {
            'raw_document_id': raw_doc.id,
            'current_status': raw_doc.status,
            'status_display': raw_doc.get_status_display(),
            'metadata': raw_doc.metadata,
        }
    })

@login_required
@require_POST
def trigger_ai_learn_document_view(request, group_id, document_id):
    """
    🧠 Trích xuất tri thức thô từ tài liệu trong khung chat, tạo bản ghi RawDocument (PENDING)
    và kích hoạt Celery Task (P1) để tiến hành bóc tách cấu trúc ngầm.
    Tuân thủ quy tắc: Cấm tuyệt đối đẩy dữ liệu pending/staging vào Vector Store.
    """
    # 🔒 [Group-Centric]: Cô lập tuyệt đối, đảm bảo tài liệu thuộc đúng group_id trên URL
    document = get_object_or_404(Document, id=document_id, group_id=group_id)
    group = document.group

    # 🔒 Kiểm tra quyền thành viên theo mô hình Group-Centric tuyệt đối
    if not group.memberships.filter(user=request.user).exists():
        logger.warning(f"🛡️ [Security] User {request.user.id} cố gắng truy cập tài liệu nhóm {group.id} không có quyền.")
        return JsonResponse({
            'status': 'error',
            'message': 'Bạn không có quyền thao tác trên tài liệu của nhóm này.'
        }, status=403)

    try:
        logger.info(f"📚 [AILearn] Đang trích xuất tài liệu ID: {document.id} cho Group ID: {group.id}")

        extracted_content = ""
        file_type = ""
        if document.file:
            file_type = document.file.name.split('.')[-1].lower()
            try:
                extracted_content = FileProcessor.extract_text_from_file(document.file.path)
            except Exception as parse_err:
                logger.warning(f"⚠️ Không thể parse file trực tiếp, dùng tên file: {parse_err}")
                extracted_content = f"Tài liệu: {document.file.name}"

        # 📂 Tạo hoặc cập nhật bản ghi RawDocument với trạng thái 'PENDING' chuẩn Model choices
        raw_doc, created = RawDocument.objects.get_or_create(
            document=document,
            defaults={
                'group': group,
                'status': 'PENDING',
                'raw_content': extracted_content or f"Tài liệu: {document.file.name}",
                'file': document.file,
                'file_type': file_type
            }
        )
        
        if not created:
            raw_doc.raw_content = extracted_content or raw_doc.raw_content
            raw_doc.status = 'PENDING'
            raw_doc.file = document.file
            raw_doc.file_type = file_type
            raw_doc.save(update_fields=['raw_content', 'status', 'file', 'file_type'])

        # 🛑 QUY TẮC VÀNG: Tuyệt đối không tương tác với Vector Store tại đây.
        # Dữ liệu nằm ở RawDocument ở trạng thái PENDING/staging chờ Audit Agent xử lý.

        # ⚙️ Kích hoạt Celery Task (P1 - Background) để xử lý bóc tách bất đồng bộ
        task = process_document_task.delay(
            raw_document_id=raw_doc.id,
            group_id=str(group.id),
            user_id=request.user.id
        )

        logger.info(f"🚀 [Celery P1] Đã đẩy RawDocument ID {raw_doc.id} vào hàng đợi xử lý. Task ID: {task.id}")

        return JsonResponse({
            'status': 'success',
            'message': 'Tài liệu đã được đưa vào phân vùng Staging và kích hoạt tiến trình phân tích ngầm!',
            'raw_document_id': raw_doc.id,
            'task_id': task.id
        })

    except Exception as e:
        logger.error(f"❌ [AILearn Error] Lỗi khi trích xuất tài liệu ID {document_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Lỗi hệ thống khi trích xuất: {str(e)}'
        }, status=500)