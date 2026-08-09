"""
Module: apps.ai_assistant.engine
Author: Kiến trúc sư VnxChatBot & Senior Software Engineer
Description: 
    Engine lõi (AI_Engine) đảm nhận việc trích xuất văn bản thô, phân tích sâu tài liệu,
    gắn nhãn chủ đề, ngữ cảnh (context_tag), chấm điểm tin cậy (Confidence Score)
    và kiểm tra mâu thuẫn tri thức trước khi đưa vào vòng đời phê duyệt.
"""

import os
import json
import logging
from django.conf import settings
from apps.ai_assistant.services.ai_factory import AIFactory

logger = logging.getLogger(__name__)

class AI_Engine:
    """
    Class: AI_Engine
    Description: 
        Bộ máy phân tích AI thông minh, hỗ trợ bóc tách tài liệu đa định dạng,
        sinh metadata cấu trúc và đánh giá xung đột tri thức trong phạm vi nhóm (Group-Centric).
    """

    @staticmethod
    def _extract_text(file_path: str) -> str:
        """Helper tách text dựa trên đuôi file."""
        if not os.path.exists(file_path):
            logger.error(f"❌ [AI_Engine] Không tìm thấy file tại đường dẫn: {file_path}")
            return ""
        
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in ['.txt', '.md', '.csv', '.json']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif ext == '.pdf':
                from apps.ai_assistant.services.document_processor import DocumentProcessorService
                return DocumentProcessorService.extract_text(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"❌ [AI_Engine Error] Lỗi đọc file {file_path}: {str(e)}")
            return ""

    @staticmethod
    def _parse_llm_response(response) -> dict:
        """Làm sạch và phân tích kết quả trả về dạng JSON từ LLM an toàn."""
        if isinstance(response, dict):
            return response
        
        cleaned = str(response).strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("⚠️ [AI_Engine] Không thể parse JSON trực tiếp từ phản hồi LLM. Đang cố gắng trích xuất thô.")
            return {"raw_output": response}

    @classmethod
    def extract_and_score(cls, file_path: str, group=None) -> tuple[dict, float]:
        """
        Trích xuất nội dung, chấm điểm tin cậy (Confidence Score) từ 0.0 đến 1.0,
        và phân loại sơ bộ thông tin từ file tài liệu.
        """
        raw_text = cls._extract_text(file_path)
        
        if len(raw_text) < 50:
            return {
                "content": "Dữ liệu quá ngắn hoặc không thể đọc",
                "confidence": 0.0,
                "context_tag": "unprocessed",
                "source_reference": file_path,
                "has_conflict": False
            }, 0.0

        try:
            # Lấy group_id an toàn dù truyền object ChatGroup hay int ID
            group_id = group.id if hasattr(group, 'id') else group
            llm_client = AIFactory.get_provider(group_id=group_id)
        except Exception as e:
            logger.warning(f"⚠️ [AI_Engine] Không thể khởi tạo LLM Provider, dùng giá trị mặc định: {str(e)}")
            return {
                "content": raw_text[:2000],
                "confidence": 0.5,
                "context_tag": "general",
                "source_reference": file_path,
                "has_conflict": False
            }, 0.5

        prompt = f"""
Bạn là hệ thống phân tích tri thức chuyên sâu. Hãy phân tích nội dung tài liệu sau đây và trả về kết quả định dạng JSON thuần túy (không kèm markdown block) gồm các trường:
- "content": "Nội dung tóm tắt sạch sẽ, chuẩn hóa để đưa vào hệ thống tri thức",
- "confidence": 0.95,
- "context_tag": "Chủ đề chính hoặc tên nghiệp vụ liên quan (ví dụ: Quy trình, Tài chính, Kỹ thuật)",
- "source_reference": "{file_path}",
- "has_conflict": false,
- "conflict_note": "Ghi chú nếu có mâu thuẫn với tri thức cũ, ngược lại để trống"

Nội dung tài liệu: {raw_text[:3000]}
"""
        try:
            if hasattr(llm_client, 'generate_sync'):
                response = llm_client.generate_sync(prompt)
            else:
                response = llm_client.generate(prompt)
            
            parsed_data = cls._parse_llm_response(response)
            return {
                "content": parsed_data.get("content", raw_text[:1000]),
                "confidence": float(parsed_data.get("confidence", 0.85)),
                "context_tag": parsed_data.get("context_tag", "general"),
                "source_reference": parsed_data.get("source_reference", file_path),
                "has_conflict": bool(parsed_data.get("has_conflict", False)),
                "conflict_note": parsed_data.get("conflict_note", "")
            }, float(parsed_data.get("confidence", 0.85))
        except Exception as e:
            logger.error(f"❌ [AI_Engine Error] Lỗi khi gọi LLM phân tích: {str(e)}")
            return {
                "content": raw_text[:1000],
                "confidence": 0.5,
                "context_tag": "general",
                "source_reference": file_path,
                "has_conflict": True,
                "conflict_note": f"Lỗi phân tích tự động: {str(e)}"
            }, 0.5

    @classmethod
    def deep_analyze_document(cls, knowledge_unit) -> dict:
        """
        Thực hiện phân tích sâu tài liệu gắn với KnowledgeUnit:
        - Trích xuất nội dung, sinh câu hỏi gợi ý (suggested_queries).
        - Gắn nhãn ngữ cảnh và kiểm tra mâu thuẫn (conflict_warning) với kho tri thức đã approved của nhóm.
        """
        if not knowledge_unit.document or not knowledge_unit.document.file:
            return {"status": "failed", "error": "Missing file"}

        file_path = knowledge_unit.document.file.path
        group_id = knowledge_unit.group_id

        # 1. Trích xuất và chấm điểm cơ bản
        base_result, confidence = cls.extract_and_score(file_path, group=group_id)
        raw_text = cls._extract_text(file_path)

        # 2. Truy vấn kho tri thức đã duyệt ('approved') của nhóm để kiểm tra mâu thuẫn (Tenant Isolation)[cite: 1]
        from apps.group_chat.models import KnowledgeUnit
        existing_approved_units = KnowledgeUnit.objects.filter(
            document__group_id=group_id,
            status='approved'
        ).exclude(id=knowledge_unit.id)[:5]

        approved_snippets = "\n---\n".join([u.content[:500] for u in existing_approved_units])

        # 3. Gọi LLM phân tích sâu và đối chiếu mâu thuẫn
        try:
            llm_client = AIFactory.get_provider(group_id=group_id)
            prompt = f"""
Bạn là chuyên gia kiểm định tri thức hệ thống vnxChatBot. 
Hãy phân tích tài liệu mới và đối chiếu với kho tri thức đã được phê duyệt của nhóm.

[TRI THỨC ĐÃ PHÊ DUYỆT HIỆN TẠI]:
{approved_snippets if approved_snippets else "Chưa có tri thức nào được duyệt."}

[TÀI LIỆU MỚI CẦN PHÂN TÍCH]:
{raw_text[:4000]}

Hãy trả về kết quả dưới dạng JSON thuần túy (không có markdown code block) với cấu trúc sau:
{{
  "suggested_queries": ["câu hỏi gợi ý 1", "câu hỏi gợi ý 2", "câu hỏi gợi ý 3"],
  "has_conflict": true/false,
  "conflict_reason": "Mô tả ngắn gọn lý do mâu thuẫn nếu có, ngược lại để trống",
  "entity_name": "Tên thực thể chính được đề cập (nếu có)"
}}
"""
            if hasattr(llm_client, 'generate_sync'):
                response = llm_client.generate_sync(prompt)
            else:
                response = llm_client.generate(prompt)

            analysis_result = cls._parse_llm_response(response)
            
            # Cập nhật trực tiếp lên KnowledgeUnit
            knowledge_unit.content = raw_text
            knowledge_unit.category = base_result.get("context_tag", "General")
            knowledge_unit.context_tag = analysis_result.get("entity_name", base_result.get("context_tag", "general"))
            knowledge_unit.has_conflict = bool(analysis_result.get("has_conflict", base_result.get("has_conflict", False)))
            knowledge_unit.conflict_reason = analysis_result.get("conflict_reason", base_result.get("conflict_note", ""))
            knowledge_unit.suggested_queries = analysis_result.get("suggested_queries", [])
            knowledge_unit.confidence_score = confidence
            knowledge_unit.status = 'pending'
            knowledge_unit.save()

            return {
                "status": "success",
                "has_conflict": knowledge_unit.has_conflict,
                "confidence_score": knowledge_unit.confidence_score
            }
        except Exception as e:
            logger.error(f"❌ [AI_Engine Deep Analysis Error] {str(e)}")
            knowledge_unit.status = 'pending'
            knowledge_unit.save(update_fields=['status'])
            return {"status": "error", "message": str(e)}