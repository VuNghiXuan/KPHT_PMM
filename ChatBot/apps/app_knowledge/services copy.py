import json
import logging
import re
from tqdm import tqdm
from django.utils import timezone
from .ai_gateway import AIGateway
from .models import KnowledgeDraft, LearningLog
from apps.app_coach.models import DataType

logger = logging.getLogger(__name__)

class KnowledgeService:
    
    @staticmethod
    def auto_assign_data_type(draft):
        """
        TỰ ĐỘNG PHÂN LOẠI NÂNG CAO: Dựa trên danh sách chức năng từ image_666d1d.png
        """
        if draft.data_type:
            return draft.data_type

        intel = draft.sheet.metadata
        sheet_name = draft.sheet.name.lower()
        fields = str(intel.get("business_data", [])).lower()
        logic = str(intel.get("logic_blocks", [])).lower()
        all_context = f"{sheet_name} {fields} {logic}"

        # 1. Nhóm CẦM ĐỒ (Module 4) - Logic phức tạp nhất
        if any(word in all_context for word in ['cầm đồ', 'chuộc đồ', 'gia hạn', 'lãi suất', 'thanh lý', 'biên nhận']):
            dt, _ = DataType.objects.get_or_create(
                code="PAWN", 
                defaults={'name': "Nghiệp vụ Cầm đồ", 'ai_model_preference': 'OLLAMA'}
            )
            draft.data_type = dt

        # 2. Nhóm MUA BÁN & ĐỔI BÙ (Module 3)
        elif any(word in all_context for word in ['mua bán', 'đổi bù', 'mua dẻ', 'ngoại tệ', 'hóa đơn']):
            dt, _ = DataType.objects.get_or_create(
                code="TRADING", 
                defaults={'name': "Mua bán - Giao dịch", 'ai_model_preference': 'GROQ'}
            )
            draft.data_type = dt

        # 3. Nhóm QUẢN LÝ THỢ & GIA CÔNG (Module 8)
        elif any(word in all_context for word in ['thợ', 'giao nhận', 'tiền công', 'hao hụt', 'gia công']):
            dt, _ = DataType.objects.get_or_create(
                code="CRAFTSMAN", 
                defaults={'name': "Quản lý Thợ & Gia công", 'ai_model_preference': 'OLLAMA'}
            )
            draft.data_type = dt

        # 4. Nhóm KHO & SẢN PHẨM (Module 2, 7, 10)
        elif any(word in all_context for word in ['vàng', 'nhập kho', 'xuất kho', 'chuyển kho', 'tem', 'bảng giá', 'soạn dẻ']):
            dt, _ = DataType.objects.get_or_create(
                code="INVENTORY", 
                defaults={'name': "Quản lý Kho & Sản phẩm", 'ai_model_preference': 'OLLAMA'}
            )
            draft.data_type = dt

        # 5. Nhóm KẾ TOÁN & THUẾ (Module 9)
        elif any(word in all_context for word in ['doanh thu', 'chi phí', 'lợi nhuận', 'thuế', 'công nợ', 'tạm ứng']):
            dt, _ = DataType.objects.get_or_create(
                code="ACCOUNTING", 
                defaults={'name': "Kế toán & Tài chính", 'ai_model_preference': 'GROQ'}
            )
            draft.data_type = dt

        # 6. Nhóm MARKETING & CSKH (Module 5, 6)
        elif any(word in all_context for word in ['voucher', 'quà tặng', 'chiến dịch', 'marketing', 'tích lũy', 'khách hàng', 'khiếu nại']):
            dt, _ = DataType.objects.get_or_create(
                code="MARKETING_CRM", 
                defaults={'name': "Marketing & CSKH", 'ai_model_preference': 'GROQ'}
            )
            draft.data_type = dt

        # 7. Mặc định: HỆ THỐNG & TIN TỨC (Module 1, 11)
        else:
            dt, _ = DataType.objects.get_or_create(
                code="SYSTEM", 
                defaults={'name': "Hệ thống & Tiện ích", 'ai_model_preference': 'GROQ'}
            )
            draft.data_type = dt
        
        draft.save()
        return draft.data_type

    @staticmethod
    def _get_learned_context(project):
        """
        KẾT NỐI TRI THỨC: Lấy những gì anh Vũ đã dạy để nạp vào Context.
        """
        learned_logs = LearningLog.objects.filter(project=project, is_learned=True)
        if not learned_logs.exists():
            return ""
        
        context_parts = ["\n--- 🧠 TRI THỨC HỆ THỐNG ĐÃ HỌC TỪ ANH VŨ ---"]
        for log in learned_logs:
            context_parts.append(f"Tình huống: {log.question}\nGiải đáp: {log.admin_answer}")
        
        return "\n\n".join(context_parts) + "\n--- (Hãy áp dụng tri thức trên để phân tích) ---\n"

    @staticmethod
    def _extract_and_log_questions(draft, content):
        """
        BÁO HIỆU HỎI BÀI: Bóc tách mục [⚠️ GÓC PHẢN BIỆN] để hiển thị dấu ? đỏ trên GUI.
        """
        # Nếu AI báo "Dữ liệu logic đã ổn" thì coi như không có câu hỏi
        if "dữ liệu logic đã ổn" in content.lower():
            return False

        # Tìm nội dung nằm sau mục phản biện
        pattern = r"\[⚠️\s*(?:GÓC PHẢN BIỆN|Cần xác nhận)\](.*)"
        match = re.search(pattern, content, re.S | re.I)
        
        if match:
            question_content = match.group(1).strip()
            # Chỉ log nếu câu hỏi có nội dung thực sự (không phải chỉ vài ký tự trắng)
            if len(question_content) > 10:
                LearningLog.objects.get_or_create(
                    project=draft.project,
                    question=f"Sheet {draft.sheet.name}: {question_content[:500]}",
                    defaults={'is_learned': False}
                )
                return True
        return False

    @staticmethod
    def refine_draft(draft_id, current_idx=1, total=1):
        """
        Xử lý tinh chế chuyên sâu cho 1 nghiệp vụ.
        """
        try:
            draft = KnowledgeDraft.objects.select_related('sheet', 'project', 'data_type').get(id=draft_id)
            sheet = draft.sheet

            print(f"\n--- [AI COACH] {current_idx}/{total} | {sheet.name} ---")

            # Bước 1: Tự động gán nhãn DataType nếu chưa có
            data_type = KnowledgeService.auto_assign_data_type(draft)

            # Bước 2: Chuẩn bị Prompt (Lấy từ DataType hoặc dùng Default)
            default_system = (
                "Bạn là Chuyên gia BA cao cấp cho hệ thống 'Ứng Dụng Vàng' (KPHT).\n"
                "NHIỆM VỤ: Chuyển Metadata kỹ thuật thành HDSD nghiệp vụ thực tế.\n\n"
                "CHỈ THỊ VỀ ĐỘ TỰ TIN (QUAN TRỌNG):\n"
                "1. TỰ SUY LUẬN: Dựa vào kiến thức ngành vàng (vàng quy tuổi, lãi suất, tiền công), nếu Metadata thiếu nhưng bạn có thể suy luận logic đạt độ tin cậy > 85%, hãy TỰ HOÀN THIỆN nội dung và không đặt câu hỏi.\n"
                "2. KHÔNG HỎI VẶT: Không hỏi về các trường dữ liệu hiển thị đơn giản (Tên, Ngày, Ghi chú). Chỉ hỏi về logic tính toán hoặc luồng đi của tiền/hàng nếu bị đứt đoạn.\n\n"
                "CẤU TRÚC ĐẦU RA BẮT BUỘC:\n"
                " - 🎯 MỤC ĐÍCH: Ý nghĩa thực tế.\n"
                " - 🔄 LUỒNG NGHIỆP VỤ: Các bước nhân viên làm (Tự suy luận từ Metadata).\n"
                " - ⚙️ PHÂN TÍCH LOGIC SÂU: Công thức tính, dòng tiền, dòng hàng.\n\n"
                " - [⚠️ GÓC PHẢN BIỆN]:\n"
                "   + CHỈ ĐẶT CÂU HỎI KHI: Metadata mâu thuẫn trực tiếp (ví dụ: tiền vào mà không có hàng ra) hoặc bạn hoàn toàn không thể đoán định được công thức (độ tin cậy < 50%).\n"
                "   + Nếu ổn hoặc đã tự suy luận được: Ghi chính xác 'Dữ liệu logic đã ổn, không có nghi vấn'.\n"
            )
            system_p = data_type.system_prompt if (data_type and data_type.system_prompt) else default_system
            
            # Bước 3: Nạp tri thức và Metadata
            learned_context = KnowledgeService._get_learned_context(draft.project)
            intel = sheet.metadata
            metadata_str = json.dumps({
                "logic": intel.get("logic_blocks", []), 
                "fields": intel.get("business_data", [])
            }, ensure_ascii=False, indent=2)

            full_user_content = (
                f"{learned_context}\n"
                f"Hãy phân tích nghiệp vụ cho Sheet: '{sheet.name}'\n"
                f"Metadata: {metadata_str}"
            )

            # Bước 4: Gọi AI (Ưu tiên theo cấu hình DataType)
            full_prompt = f"System: {system_p}\n\nUser: {full_user_content}"
            ai = AIGateway(full_prompt)
            
            # Chọn model: Ưu tiên DataType -> Token count -> Default
            use_ollama = (data_type.ai_model_preference == 'OLLAMA') or (ai.token_count > 4000)
            
            final_content = ai.process_ai_knowledge(full_prompt, use_ollama=use_ollama)

            # Bước 5: Cập nhật kết quả và trạng thái (Để hiện dấu ? trên GUI)
            if final_content and final_content.strip():
                draft.content = final_content.strip()
                has_questions = KnowledgeService._extract_and_log_questions(draft, final_content)
                
                if has_questions:
                    draft.status = 'PENDING' # Trạng thái này sẽ kích hoạt dấu ? đỏ trên GUI
                else:
                    draft.status = 'AI_READY' # Trạng thái đã xong, anh chỉ việc duyệt
                
                draft.updated_at = timezone.now()
                draft.save()
                return True
            
            return False

        except Exception as e:
            logger.error(f"Lỗi Tinh chế {draft_id}: {str(e)}")
            return False

    @staticmethod
    def refine_all_project_drafts(project_id):
        """
        CHẠY HÀNG LOẠT 211 NGHIỆP VỤ.
        """
        # drafts = KnowledgeDraft.objects.filter(project_id=project_id, sheet__isnull=False)
        # Kiểm tra tổng số draft không cần điều kiện
        total_in_db = KnowledgeDraft.objects.count()
        print(f"DEBUG: Tổng số bản ghi Draft trong DB: {total_in_db}")

        drafts = KnowledgeDraft.objects.filter(project_id=project_id)
        print(f"DEBUG: Số lượng Draft thuộc Project {project_id}: {drafts.count()}")

        total = drafts.count()
        success_count = 0
        
        for i, draft in enumerate(tqdm(drafts, desc="Đang quét nghiệp vụ", unit="sheet")):
            if KnowledgeService.refine_draft(draft.id, current_idx=i+1, total=total):
                success_count += 1
        
        print(f"\n✨ HOÀN THÀNH: {success_count}/{total} nghiệp vụ đã được xử lý.")