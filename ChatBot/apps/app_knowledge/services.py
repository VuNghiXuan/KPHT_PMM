import json
import logging
import re
from tqdm import tqdm
from django.utils import timezone
from .ai_gateway import AIGateway
from .models import KnowledgeDraft
from .models import LearningLog

logger = logging.getLogger(__name__)

class KnowledgeService:
    @staticmethod
    def _get_learned_context(project):
        """
        Hàm phụ: Gom tất cả những gì anh Vũ đã dạy để nạp vào Context cho AI.
        """
        learned_logs = LearningLog.objects.filter(project=project, is_learned=True)
        if not learned_logs.exists():
            return ""
        
        context_parts = ["--- CÁC TRI THỨC ĐÃ HỌC TỪ HỆ THỐNG ---"]
        for log in learned_logs:
            context_parts.append(f"Câu hỏi: {log.question}\nTrả lời: {log.admin_answer}")
        
        return "\n\n".join(context_parts) + "\n-----------------------------------\n"

    @staticmethod
    def _extract_and_log_questions(draft, content):
        """
        Hàm phụ: Dùng Regex bóc tách mục [❓ CẦN ANH VŨ GIẢI THÍCH] và lưu vào Nhật ký.
        """
        # Tìm nội dung nằm sau mục câu hỏi (không phân biệt hoa thường)
        pattern = r"\[❓\s*(?:CẦN ANH VŨ GIẢI THÍCH|Cần giải thích|Cần xác nhận)\](.*)"
        match = re.search(pattern, content, re.S | re.I)
        
        if match:
            question_content = match.group(1).strip()
            if question_content:
                # Lưu vào nhật ký AI hỏi bài để anh Vũ trả lời
                LearningLog.objects.get_or_create(
                    project=draft.project,
                    question=f"Sheet {draft.sheet.name}: {question_content[:500]}", # Giới hạn 500 ký tự cho tiêu đề log
                    defaults={'is_learned': False}
                )
                return True
        return False

    @staticmethod
    def refine_draft(draft_id, current_idx=1, total=1):
        """
        Xử lý tinh chế cho DUY NHẤT 1 dòng Draft.
        """
        try:
            draft = KnowledgeDraft.objects.select_related('sheet', 'project', 'data_type').get(id=draft_id)
            sheet = draft.sheet

            print(f"\n--- [AI Tinh Chế] {current_idx}/{total} | Sheet: {sheet.name} ---")

            if not sheet or not sheet.metadata:
                print(f"⚠️ Bỏ qua: Sheet '{sheet.name}' không có metadata.")
                return False

            # 1. Lấy Prompt từ Admin hoặc dùng bản Default "Nghiệp vụ sâu"
            default_system = (
                "Bạn là Trợ lý Chuyên gia Phân tích Nghiệp vụ (BA) của hệ thống 'Ứng Dụng Vàng' (KPHT). "
                "Nhiệm vụ: Chuyển đổi Metadata kỹ thuật từ Excel thành Bản hướng dẫn nghiệp vụ (HDSD) thực tế cho nhân viên tiệm vàng.\n\n"
                "NGUYÊN TẮC LÀM VIỆC:\n"
                "1. KHÔNG liệt kê mã ô (A1, B2, C18...). Hãy gọi bằng tên nhãn (Label) của trường đó.\n"
                "2. KHÔNG giải thích cấu trúc JSON. Hãy giải thích quy trình nghiệp vụ: Tiền từ đâu ra, tính phí thế nào, bấm nút thì chuyện gì xảy ra.\n"
                "3. NGÔN NGỮ: Tiếng Việt chuyên ngành vàng (Vàng quy tuổi, Tiền công, Chênh lệch, Thu hộ...).\n"
                "4. CẤU TRÚC ĐẦU RA BẮT BUỘC:\n"
                "   - 🎯 MỤC ĐÍCH: Sheet này dùng để làm gì trong tiệm vàng?\n"
                "   - 📥 THÔNG TIN NHẬP LIỆU: Nhân viên cần điền những gì? Trường nào bắt buộc?\n"
                "   - ⚙️ LOGIC TÍNH TOÁN & RÀNG BUỘC: Giải mã các công thức (Ví dụ: Tổng thanh toán = Tiền gốc + Phí). Giải thích các nút bấm 'Hoàn tất' sẽ cập nhật kho hay quỹ thế nào.\n"
                "   - ❓ CẦN ANH VŨ XÁC NHẬN: Liệt kê các câu hỏi về logic mà Metadata chưa nói rõ (Ví dụ: Phí này tính theo % hay số cố định?)"
            )

            default_user = (
                "Chào chuyên gia, hãy phân tích nghiệp vụ cho Sheet: '{{sheet_name}}'.\n\n"
                "Dữ liệu Metadata bóc tách từ Excel:\n"
                "--- START METADATA ---\n"
                "{{metadata}}\n"
                "--- END METADATA ---\n\n"
                "Yêu cầu: Viết bản HDSD ngắn gọn, tập trung vào logic tính toán và các bước thực hiện. "
                "Nếu thấy logic liên quan đến 'Phí chuyển đổi' hoặc 'Số dư tài khoản', hãy phân tích cực kỹ phần này cho anh Vũ."
            )

            # Ưu tiên lấy từ DataType (Admin), nếu không có mới dùng Default ở trên
            system_p = draft.data_type.system_prompt if (draft.data_type and draft.data_type.system_prompt) else default_system
            user_template = draft.data_type.user_prompt_template if (draft.data_type and draft.data_type.user_prompt_template) else default_user
            # 2. Nạp TRI THỨC ĐÃ HỌC (Nhật ký tự học)
            learned_context = KnowledgeService._get_learned_context(draft.project)

            # 3. Chuẩn bị Metadata
            intel = sheet.metadata
            metadata_str = json.dumps({
                "logic": intel.get("logic_blocks", []), 
                "fields": intel.get("business_data", [])
            }, ensure_ascii=False, indent=2)

            # Thay thế biến template
            user_p = user_template.replace("{{sheet_name}}", sheet.name).replace("{{metadata}}", metadata_str)
            
            # Gắn context tri thức vào đầu user prompt
            full_user_content = f"{learned_context}\n{user_p}"
            full_prompt = f"System: {system_p}\n\nUser: {full_user_content}"

            # 4. Gọi AI Gateway (Tự động chọn Ollama nếu data lớn)
            ai = AIGateway(full_prompt)
            use_ollama = ai.token_count > 4000
            
            mode_text = "Ollama (Local)" if use_ollama else "Groq (Cloud)"
            print(f"🤖 Đang gọi {mode_text}... ({ai.token_count} tokens)")

            final_content = ai.process_ai_knowledge(full_prompt, use_ollama=use_ollama)

            # 5. Xử lý kết quả & Ghi log hỏi bài
            if final_content and final_content.strip():
                draft.content = final_content.strip()
                
                # Check xem AI có đặt câu hỏi không
                has_questions = KnowledgeService._extract_and_log_questions(draft, final_content)
                
                if has_questions:
                    draft.status = 'PENDING'
                    print(f"💡 Kết quả: AI đã đặt câu hỏi -> Xem tại 'AI Hỏi bài'")
                else:
                    draft.status = 'AI_READY'
                    print(f"✅ Kết quả: Đã xong (Không có nghi vấn)")
                
                draft.save()
                return True
            
            return False

        except Exception as e:
            print(f"❌ Lỗi tại Sheet {draft_id}: {str(e)}")
            return False

    @staticmethod
    def refine_all_project_drafts(project_id):
        """
        HÀM CHẠY HÀNG LOẠT: Tinh chế toàn bộ Draft của 1 Project.
        """
        drafts = KnowledgeDraft.objects.filter(project_id=project_id, sheet__isnull=False)
        total = drafts.count()
        
        print(f"\n🚀 BẮT ĐẦU TINH CHẾ HÀNG LOẠT: {total} Sheets")
        
        success_count = 0
        # Sử dụng tqdm làm thanh tiến trình
        for i, draft in enumerate(tqdm(drafts, desc="Đang tinh chế", unit="sheet")):
            res = KnowledgeService.refine_draft(draft.id, current_idx=i+1, total=total)
            if res:
                success_count += 1
        
        print(f"\n✨ HOÀN THÀNH: Đã tinh chế thành công {success_count}/{total} sheets.")