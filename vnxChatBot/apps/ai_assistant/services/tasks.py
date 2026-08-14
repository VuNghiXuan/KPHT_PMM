import logging
from celery import current_app
from apps.group_chat.models import Document, KnowledgeUnit

logger = logging.getLogger(__name__)

@current_app.task(bind=True, queue='documents_p1_processing')
def process_document_task(self, document_id, group_id):
    """
    Task xử lý file từ Document thô -> KnowledgeUnit(status='staging').
    Sử dụng send_task để tránh circular import.
    """
    from apps.ai_assistant.services.parser import DocumentParserService

    try:
        document = Document.objects.get(id=document_id)
        logger.info(f"🚀 [ProcessDocument] Bắt đầu xử lý file: {document.file.name} (Group: {group_id})")

        # 1. Bóc tách nội dung
        parser = DocumentParserService.get_parser_for_file(document.file_extension)
        parsed_data = parser.parse(document.file.path)

        # 2. Tạo các đơn vị tri thức ở trạng thái 'staging'
        for item in parsed_data:
            knowledge_unit = KnowledgeUnit.objects.create(
                document=document,
                group_id=group_id,
                entity_name=document.title,
                content=item['content'],
                status='staging',
                raw_structure_json=item.get('metadata')
            )
            
            # 3. Kích hoạt phân tích mâu thuẫn bằng send_task (Tránh import lỗi)
            current_app.send_task(
                'apps.ai_assistant.tasks.conflict_analysis_task',
                args=[knowledge_unit.id],
                queue='conflicts'
            )

        logger.info(f"✅ [ProcessDocument] Đã tạo staging units cho document {document_id}")
        return f"Document {document_id} đã được parsing và đẩy vào trạng thái staging."

    except Document.DoesNotExist:
        logger.error(f"❌ [ProcessDocument] Tài liệu {document_id} không tồn tại.")
        return "Error: Document not found"
    except Exception as exc:
        logger.error(f"❌ [ProcessDocument] Lỗi xử lý file: {str(exc)}")
        raise self.retry(exc=exc)

@current_app.task(bind=True, queue='conflicts')
def conflict_analysis_task(self, knowledge_unit_id):
    """
    Task phân tích mâu thuẫn bất đồng bộ cho một KnowledgeUnit đang ở trạng thái 'staging'.
    Sử dụng chiến lược Vectorized Pre-filtering giới hạn theo group_id.
    """
    try:
        # 1. Lấy KnowledgeUnit hiện tại cần kiểm tra
        target_unit = KnowledgeUnit.objects.get(id=knowledge_unit_id)
        
        if target_unit.status != 'staging':
            logger.warning(f"⚠️ [ConflictAnalysis] Unit {knowledge_unit_id} không ở trạng thái staging. Bỏ qua.")
            return f"Bỏ qua unit {knowledge_unit_id}"

        logger.info(f"🔍 [ConflictAnalysis] Đang quét mâu thuẫn cho Unit ID: {knowledge_unit_id} (Group: {target_unit.group_id})")

        # 2. Truy vấn các bản ghi đã 'approved' trong cùng một group_id (Hard Scoping)
        # Loại trừ chính nó nếu có trường hợp tái kiểm tra
        approved_units = KnowledgeUnit.objects.filter(
            group_id=target_unit.group_id,
            status='approved'
        ).exclude(id=target_unit.id)

        if not approved_units.exists():
            logger.info(f"✨ [ConflictAnalysis] Group {target_unit.group_id} chưa có dữ liệu approved nào. Không có mâu thuẫn.")
            return f"Unit {knowledge_unit_id}: Sạch, không có dữ liệu đối chiếu."

        # 3. Thực hiện Vector Similarity Search (Pre-filtering)
        # Ở cấp độ kiến trúc hệ thống, ta gọi Vector Store service để tính Cosine Similarity
        from apps.ai_assistant.services.ai_engine import AIEngineService
        
        # Giả lập hoặc gọi hàm tính độ tương đồng cao nhất trong VectorDB với metadata group_id
        # Trả về top match gồm: (matched_unit_id, similarity_score, matched_content)
        top_matches = AIEngineService.find_most_similar_units(
            query_text=target_unit.content,
            group_id=target_unit.group_id,
            top_k=3
        )

        conflict_found = False
        conflict_details = []

        # Ngưỡng phát hiện trùng lặp / mâu thuẫn (> 0.85)
        OVERLAP_THRESHOLD = 0.85

        for match in top_matches:
            score = match.get('score', 0.0)
            if score >= OVERLAP_THRESHOLD:
                conflict_found = True
                conflict_details.append({
                    "matched_unit_id": match.get('unit_id'),
                    "similarity_score": score,
                    "snippet": match.get('content')[:200] # Lưu đoạn trích xuất ngắn
                })

        # 4. Cập nhật trạng thái của KnowledgeUnit dựa trên kết quả kiểm tra
        if conflict_found:
            target_unit.is_conflict = True
            target_unit.conflict_report = {
                "status": "CONFLICT_DETECTED",
                "matches": conflict_details,
                "recommendation": "Đề xuất: Ghi đè (Update), Hợp nhất (Merge) hoặc Bỏ qua (Ignore)"
            }
            target_unit.save(update_fields=['is_conflict', 'conflict_report'])
            logger.warning(f"⚠️ [Conflict Conflict] Phát hiện mâu thuẫn cho Unit ID {knowledge_unit_id} với ngưỡng >= {OVERLAP_THRESHOLD}")
        else:
            target_unit.is_conflict = False
            target_unit.conflict_report = {"status": "CLEAN", "max_score": top_matches[0]['score'] if top_matches else 0.0}
            target_unit.save(update_fields=['is_conflict', 'conflict_report'])
            logger.info(f"✅ [Conflict Clean] Unit ID {knowledge_unit_id} không có xung đột nội dung.")

        return f"Hoàn tất phân tích mâu thuẫn cho unit {knowledge_unit_id}. Conflict: {conflict_found}"

    except KnowledgeUnit.DoesNotExist:
        logger.error(f"❌ [ConflictError] KnowledgeUnit ID {knowledge_unit_id} không tồn tại.")
        return f"Lỗi: Không tìm thấy unit {knowledge_unit_id}"
    except Exception as exc:
        logger.error(f"❌ [ConflictException] Lỗi khi phân tích mâu thuẫn: {str(exc)}")
        raise self.retry(exc=exc)