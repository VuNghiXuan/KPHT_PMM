import json
import logging
import re
from tqdm import tqdm
from django.utils import timezone
from .models import KnowledgeDraft, LearningLog
# from apps.app_coach.models import DataType
import time
import json
import logging
import time
from django.db import transaction

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class KnowledgeService:
    
    @staticmethod
    def auto_assign_data_type(draft):
        """
        TỰ ĐỘNG PHÂN LOẠI NÂNG CAO (ADVANCED CLASSIFICATION)
        Đã bổ sung cơ chế chống chồng lấn nghiệp vụ cho hệ thống lớn.
        """
        if draft.data_type:
            return draft.data_type

        # 1. Thu thập dữ liệu ngữ cảnh
        sheet_name = draft.sheet.name.strip() if draft.sheet else "Unknown"
        sheet_name_lower = sheet_name.lower()
        
        intel = draft.sheet.metadata if draft.sheet else {}
        fields = str(intel.get("business_data", [])).lower()
        logic = str(intel.get("logic_blocks", [])).lower()
        all_context = f"{sheet_name_lower} {fields} {logic}"

        # 2. Định nghĩa các tầng lọc
        # TẦNG 0: ƯU TIÊN TUYỆT ĐỐI (System & Config) - Tránh lẫn lộn với nghiệp vụ
        priority_mapping = {
            'hướng dẫn': 'GUIDE', 'cấu hình': 'SYSTEM_CONFIG', 'thiết lập': 'SYSTEM_CONFIG',
            'setup': 'SYSTEM_CONFIG', 'danh mục': 'SYSTEM_CONFIG', 'quy định': 'GUIDE'
        }

        # TẦNG 1: MAPPING TRỰC TIẾP (Nghiệp vụ thực tế KPHT)
        direct_mapping = {
            'cầm': 'PAWN', 'chuộc': 'PAWN', 'biên nhận': 'PAWN', 'lãi': 'PAWN',
            'mua': 'TRADING', 'bán': 'TRADING', 'đổi': 'TRADING', 'ngoại tệ': 'TRADING',
            'thợ': 'CRAFTSMAN', 'gia công': 'CRAFTSMAN', 'tiền công': 'CRAFTSMAN', 'sáp': 'CRAFTSMAN',
            'kho': 'INVENTORY', 'tồn': 'INVENTORY', 'nhập': 'INVENTORY', 'xuất': 'INVENTORY', 'tem': 'INVENTORY',
            'thu': 'ACCOUNTING', 'chi': 'ACCOUNTING', 'sổ cái': 'ACCOUNTING', 'thuế': 'ACCOUNTING', 'quỹ': 'ACCOUNTING',
            'marketing': 'MARKETING_CRM', 'quà': 'MARKETING_CRM', 'khách': 'MARKETING_CRM'
        }

        best_code = None

        # Bước A: Kiểm tra Tầng Ưu Tiên (System/Guide) trước để không bị rơi vào nghiệp vụ kinh doanh
        for key, code in priority_mapping.items():
            if key in sheet_name_lower:
                best_code = code
                break

        # Bước B: Nếu không phải System/Guide, kiểm tra Tầng Mapping Trực Tiếp
        if not best_code:
            for key, code in direct_mapping.items():
                if key in sheet_name_lower:
                    best_code = code
                    break

        # Bước C: Nếu vẫn chưa ra, dùng Scoring trọng số kết hợp "Từ khóa loại trừ"
        if not best_code:
            category_weights = {
                "PAWN": {
                    'keywords': ['cầm đồ', 'gia hạn', 'thanh lý', 'tiệm cầm'],
                    'exclude': ['hướng dẫn', 'phần mềm'] # Nếu có từ này thì khả năng cao không phải nghiệp vụ cầm đồ thực tế
                },
                "TRADING": {
                    'keywords': ['hóa đơn', 'bán lẻ', 'giá mua', 'giá bán', 'bù'],
                    'exclude': []
                },
                "ACCOUNTING": {
                    'keywords': ['doanh thu', 'chi phí', 'lợi nhuận', 'công nợ', 'tạm ứng'],
                    'exclude': ['hướng dẫn']
                },
                # Thêm các nhóm khác tương tự...
            }
            
            scores = {}
            for code, config in category_weights.items():
                # Kiểm tra từ khóa loại trừ trước
                if any(ex in all_context for ex in config.get('exclude', [])):
                    scores[code] = -1 # Đánh dấu loại trừ
                    continue
                    
                # Tính điểm dựa trên từ khóa xuất hiện
                scores[code] = sum(1 for word in config['keywords'] if word in all_context)
            
            if scores:
                top_code = max(scores, key=scores.get)
                best_code = top_code if scores[top_code] > 0 else "SYSTEM"
            else:
                best_code = "SYSTEM"

        # 3. Mapping thông tin hiển thị (Cập nhật thêm các loại mới)
        mapping_data = {
            "PAWN": ("Nghiệp vụ Cầm đồ", "OLLAMA"),
            "TRADING": ("Mua bán - Giao dịch", "GROQ"),
            "CRAFTSMAN": ("Quản lý Thợ & Gia công", "OLLAMA"),
            "INVENTORY": ("Quản lý Kho & Sản phẩm", "OLLAMA"),
            "ACCOUNTING": ("Kế toán & Tài chính", "GROQ"),
            "MARKETING_CRM": ("Marketing & CSKH", "GROQ"),
            "SYSTEM_CONFIG": ("Cấu hình Hệ thống", "GROQ"),
            "GUIDE": ("Hướng dẫn sử dụng", "GROQ"),
            "SYSTEM": (f"Nghiệp vụ: {sheet_name}", "GROQ")
        }

        name, model_pref = mapping_data.get(best_code, (f"Nghiệp vụ: {sheet_name}", "GROQ"))

        # 4. Cập nhật vào Database
        from apps.app_coach.models import DataType 
        dt, created = DataType.objects.get_or_create(
            code=best_code, 
            defaults={
                'name': name, 
                'ai_model_preference': model_pref
            }
        )
        
        # Cập nhật tên linh hoạt cho các mã dùng chung
        if not created and best_code in ["SYSTEM", "SYSTEM_CONFIG", "GUIDE"]:
            dt.name = name
            dt.save(update_fields=['name'])

        draft.data_type = dt
        draft.save(update_fields=['data_type'])
        
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
    def ensure_default_config():
        """
        [AUTO-INIT] Kiểm tra và tự động tạo cấu hình Prompt mặc định 
        nếu hệ thống chưa có dữ liệu cấu hình AI.
        """
        from apps.app_ai_core.models import AIPromptConfig
        
        # Kiểm tra xem đã có bất kỳ config nào active chưa
        config = AIPromptConfig.objects.filter(is_active=True).first()
        
        if not config:
            logger.warning("⚠️ Không tìm thấy AIPromptConfig. Đang tự động tạo cấu hình mặc định...")
            
            default_system = (
                "Bạn là Chuyên gia BA cao cấp cho hệ thống 'Ứng Dụng Vàng' (KPHT).\n"
                "NHIỆM VỤ: Chuyển Metadata kỹ thuật thành HDSD nghiệp vụ thực tế.\n\n"
                "CHỈ THỊ VỀ ĐỘ TỰ TIN (QUAN TRỌNG):\n"
                "1. TỰ SUY LUẬN: Dựa vào kiến thức ngành vàng (vàng quy tuổi, lãi suất, tiền công), "
                "nếu Metadata thiếu nhưng bạn có thể suy luận logic đạt độ tin cậy > 85%, "
                "hãy TỰ HOÀN THIỆN nội dung và không đặt câu hỏi.\n"
                "2. KHÔNG HỎI VẶT: Không hỏi về các trường dữ liệu hiển thị đơn giản (Tên, Ngày, Ghi chú). "
                "Chỉ hỏi về logic tính toán hoặc luồng đi của tiền/hàng nếu bị đứt đoạn.\n\n"
                "CẤU TRÚC ĐẦU RA BẮT BUỘC:\n"
                " - 🎯 MỤC ĐÍCH: Ý nghĩa thực tế.\n"
                " - 🔄 LUỒNG NGHIỆP VỤ: Các bước nhân viên làm (Tự suy luận từ Metadata).\n"
                " - ⚙️ PHÂN TÍCH LOGIC SÂU: Công thức tính, dòng tiền, dòng hàng.\n\n"
                " - [⚠️ GÓC PHẢN BIỆN]:\n"
                "   + CHỈ ĐẶT CÂU HỎI KHI: Metadata mâu thuẫn trực tiếp hoặc độ tin cậy < 50%.\n"
                "   + Nếu ổn hoặc đã tự suy luận được: Ghi chính xác 'Dữ liệu logic đã ổn, không có nghi vấn'."
            )
            
            # Tạo mới bản ghi default (Anh chỉnh lại field name cho khớp với Model của anh nhé)
            config = AIPromptConfig.objects.create(
                name="Cấu hình BA Mặc định (Auto-generated)",
                module_code="SYSTEM",
                system_prompt=default_system,
                is_default=True,
                is_active=True,
                # provider_strategy="ollama", # Ví dụ: Anh có thể set mặc định là Ollama cho tiết kiệm
                # model_name="llama3:latest"
            )
            logger.info(f"✅ Đã khởi tạo thành công cấu hình: {config.name}")
            
        return config

    @staticmethod
    def refine_draft(draft_id, current_idx=1, total=1, external_context=None):
        """
        Xử lý tinh chế chuyên sâu cho KPHT - Tối ưu bởi Vũ Nghi Xuân.
        """
        from apps.app_ai_core.models import AIPromptConfig
        from apps.app_knowledge.models import KnowledgeDraft
        from apps.app_knowledge.ai_gateway import AIGateway 

        start_time = time.time()
        
        try:
            # Bước 1: Lấy dữ liệu
            draft = KnowledgeDraft.objects.select_related('sheet', 'project', 'data_type').get(id=draft_id)
            sheet = draft.sheet
            project = draft.project
            
            print(f"🚀 [AI COACH] {current_idx}/{total} | {sheet.name}")

            # Bước 2: DataType & Module Slug
            data_type = draft.data_type or KnowledgeService.auto_assign_data_type(draft)
            if not draft.data_type:
                draft.data_type = data_type
            
            module_slug = data_type.code if data_type else "SYSTEM"

            # Bước 3: Lấy Prompt Config (Sử dụng hàm bảo vệ ensure_default_config)
            prompt_config = AIPromptConfig.objects.filter(
                module_code=module_slug, is_active=True
            ).first() or AIPromptConfig.objects.filter(
                is_default=True, is_active=True
            ).first()

            # NẾU VẪN NULL THÌ TỰ TẠO LUÔN
            if not prompt_config:
                prompt_config = KnowledgeService.ensure_default_config()

            # Bước 4: Hợp nhất Context
            learned_context = external_context if external_context is not None else \
                              KnowledgeService._get_learned_context(project)
            
            intel = sheet.metadata or {}
            metadata_str = json.dumps({
                "logic": intel.get("logic_blocks", []), 
                "fields": intel.get("business_data", [])
            }, ensure_ascii=False, indent=2)

            full_user_content = (
                f"=== BỐI CẢNH HỆ THỐNG ===\n{learned_context}\n\n"
                f"=== NHIỆM VỤ ===\n"
                f"Phân tích nghiệp vụ chi tiết cho danh mục: '{sheet.name}'\n"
                f"Loại dữ liệu: {module_slug}\n\n"
                f"=== METADATA TỪ EXCEL ===\n{metadata_str}"
            )

            # Bước 5: Gọi Gateway AI
            final_content = ""
            try:
                ai = AIGateway(config_obj=prompt_config, input_text=full_user_content)
                final_content = ai.run_process()
            except Exception as ai_err:
                logger.error(f"❌ AI Error: {str(ai_err)}")
                draft.status = 'ERROR'
                draft.save()
                return False

            # Bước 6: Lưu kết quả
            if final_content and final_content.strip():
                with transaction.atomic():
                    draft.content = final_content.strip()
                    has_questions = KnowledgeService._extract_and_log_questions(draft, final_content)
                    draft.status = 'PENDING' if has_questions else 'AI_READY'
                    
                    duration = time.time() - start_time
                    
                    # Kiểm tra xem Model của anh thực tế dùng tên trường nào? 
                    # Giả sử là 'metadata' thay vì 'metadata_info'
                    if hasattr(draft, 'metadata'):
                        meta = draft.metadata or {}
                        meta['ai_processing_time'] = round(duration, 2)
                        draft.metadata = meta
                        update_fields = ['content', 'status', 'updated_at', 'metadata', 'data_type']
                    else:
                        # Nếu không có trường JSON nào để lưu, ta bỏ qua phần lưu duration để tránh crash
                        update_fields = ['content', 'status', 'updated_at', 'data_type']
                    
                    draft.updated_at = timezone.now()
                    draft.save(update_fields=update_fields)
                
                print(f"✅ Xong: {sheet.name} ({round(duration, 2)}s)")
                return True
            
            return False

        except Exception as e:
            logger.error(f"💥 Lỗi tại Draft {draft_id}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def refine_all_project_drafts(project_id, re_process=False):
        """
        CHẠY HÀNG LOẠT 211 NGHIỆP VỤ (Batch Processing Optimized).
        Tối ưu cho hệ thống Kim Phát Hiệp Thành:
        - re_process=True: Chạy lại toàn bộ 211 nghiệp vụ.
        - re_process=False: Chỉ xử lý những sheet chưa có content hoặc đang ở trạng thái chờ.
        """
        import time
        from tqdm import tqdm

        # 1. Lấy tri thức dùng chung từ những gì anh Vũ đã dạy (Dùng cho toàn dự án)
        shared_learned_context = KnowledgeService._get_learned_context(project_id)
        
        # 2. Query danh sách Draft
        draft_query = KnowledgeDraft.objects.filter(project_id=project_id).select_related('sheet', 'data_type')
        
        if not re_process:
            # Lọc bỏ những cái đã xong (AI_READY) nếu không muốn chạy lại
            draft_query = draft_query.exclude(status='AI_READY')

        drafts = list(draft_query)
        total = len(drafts)
        
        if total == 0:
            print(f"✅ Không có nghiệp vụ nào cần tinh chế cho Project {project_id}.")
            return 0

        print(f"\n🚀 [HTJ BATCH] Bắt đầu chiến dịch tinh chế {total} nghiệp vụ...")
        print(f"📊 Tri thức nạp kèm: {len(shared_learned_context)} ký tự.")

        success_count = 0
        fail_count = 0
        start_time = time.time()

        # 3. Vòng lặp xử lý chính
        for i, draft in enumerate(tqdm(drafts, desc="Đang quét quặng Excel", unit="sheet")):
            try:
                # --- BƯỚC 3.1: TỰ ĐỘNG GÁN MÃ VÀ NGHIỆP VỤ (MỚI THÊM) ---
                # Nếu draft chưa có data_type, gọi hàm tự trọng số của anh để gán
                if not draft.data_type:
                    KnowledgeService.auto_assign_data_type(draft)
                    # Refresh lại object từ DB để nhận data_type vừa gán
                    draft.refresh_from_db() 
                # -------------------------------------------------------

                # Gọi hàm xử lý đơn lẻ
                status = KnowledgeService.refine_draft(
                    draft.id, 
                    current_idx=i+1, 
                    total=total,
                    external_context=shared_learned_context 
                )

                if status:
                    success_count += 1 # Thêm dòng này để đếm số bản ghi thành công
                else:
                    fail_count += 1

                # 4. Kiểm soát Rate Limit
                # Nếu trong Admin chọn Groq/Gemini thì mới nên nghỉ (Sleep)
                # Nếu anh Vũ ép OLLAMA hoàn toàn cho 211 sheet thì có thể bỏ sleep để chạy max speed
                current_config = getattr(draft.data_type, 'ai_model_preference', 'OLLAMA')
                if current_config != 'OLLAMA' and (i + 1) % 10 == 0:
                    time.sleep(2) # Nghỉ 2s sau mỗi 10 sheet cho Cloud API

            except Exception as e:
                logger.error(f"❌ Lỗi tại Draft {draft.id}: {str(e)}")
                fail_count += 1
                continue

        # 5. Tổng kết
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        avg_speed = round(duration / total, 2) if total > 0 else 0

        print(f"\n{'='*60}")
        print(f"✨ HOÀN THÀNH TINH CHẾ CHO DỰ ÁN KIM PHÁT HIỆP THÀNH")
        print(f"✅ Thành công: {success_count}/{total}")
        print(f"❌ Thất bại: {fail_count}")
        print(f"⏱️ Tổng thời gian: {duration} giây")
        print(f"⚡ Tốc độ trung bình: {avg_speed} giây/nghiệp vụ")
        print(f"{'='*60}\n")
        
        return success_count

        