import json
import logging
import re
import time
from django.utils import timezone
from django.db import transaction
from .models import KnowledgeDraft, LearningLog

logger = logging.getLogger(__name__)

class KnowledgeService:
    # Bộ nhớ đệm tạm thời (Cache trong RAM) để không bị spam Query DB khi chạy 211 sheets
    _datatype_cache = {}

    @staticmethod
    def auto_assign_data_type(draft):
        """
        TỰ ĐỘNG PHÂN LOẠI NÂNG CAO (ADVANCED CLASSIFICATION)
        Đã tối ưu hóa bộ nhớ đệm RAM để càn quét 211 file Excel siêu tốc.
        """
        if draft.data_type_id:  # Check ID trực tiếp để tránh trigger query relation của Django
            return draft.data_type

        # 1. Thu thập dữ liệu ngữ cảnh
        sheet_name = draft.sheet.name.strip() if draft.sheet else "Unknown"
        sheet_name_lower = sheet_name.lower()
        
        intel = draft.sheet.metadata if draft.sheet else {}
        fields = str(intel.get("business_data", [])).lower()
        logic = str(intel.get("logic_blocks", [])).lower()
        all_context = f"{sheet_name_lower} {fields} {logic}"

        # 2. Định nghĩa các tầng lọc
        priority_mapping = {
            'hướng dẫn': 'GUIDE', 'cấu hình': 'SYSTEM_CONFIG', 'thiết lập': 'SYSTEM_CONFIG',
            'setup': 'SYSTEM_CONFIG', 'danh mục': 'SYSTEM_CONFIG', 'quy định': 'GUIDE'
        }

        direct_mapping = {
            'cầm': 'PAWN', 'chuộc': 'PAWN', 'biên nhận': 'PAWN', 'lãi': 'PAWN',
            'mua': 'TRADING', 'bán': 'TRADING', 'đổi': 'TRADING', 'ngoại tệ': 'TRADING',
            'thọ': 'CRAFTSMAN', 'gia công': 'CRAFTSMAN', 'tiền công': 'CRAFTSMAN', 'sáp': 'CRAFTSMAN',
            'kho': 'INVENTORY', 'tồn': 'INVENTORY', 'nhập': 'INVENTORY', 'xuất': 'INVENTORY', 'tem': 'INVENTORY',
            'thu': 'ACCOUNTING', 'chi': 'ACCOUNTING', 'sổ cái': 'ACCOUNTING', 'thuế': 'ACCOUNTING', 'quỹ': 'ACCOUNTING',
            'marketing': 'MARKETING_CRM', 'quà': 'MARKETING_CRM', 'khách': 'MARKETING_CRM'
        }

        best_code = None

        # Bước A: Kiểm tra Tầng Ưu Tiên (System/Guide)
        for key, code in priority_mapping.items():
            if key in sheet_name_lower:
                best_code = code
                break

        # Bước B: Kiểm tra Tầng Mapping Trực Tiếp
        if not best_code:
            for key, code in direct_mapping.items():
                if key in sheet_name_lower:
                    best_code = code
                    break

        # Bước C: Dùng Scoring trọng số kết hợp "Từ khóa loại trừ"
        if not best_code:
            category_weights = {
                "PAWN": {
                    'keywords': ['cầm đồ', 'gia hạn', 'thanh lý', 'tiệm cầm'],
                    'exclude': ['hướng dẫn', 'phần mềm']
                },
                "TRADING": {
                    'keywords': ['hóa đơn', 'bán lẻ', 'giá mua', 'giá bán', 'bù'],
                    'exclude': []
                },
                "ACCOUNTING": {
                    'keywords': ['doanh thu', 'chi phí', 'lợi nhuận', 'công nợ', 'tạm ứng'],
                    'exclude': ['hướng dẫn']
                }
            }
            
            scores = {}
            for code, config in category_weights.items():
                if any(ex in all_context for ex in config.get('exclude', [])):
                    scores[code] = -1
                    continue
                scores[code] = sum(1 for word in config['keywords'] if word in all_context)
            
            if scores:
                top_code = max(scores, key=scores.get)
                best_code = top_code if scores[top_code] > 0 else "SYSTEM"
            else:
                best_code = "SYSTEM"

        # Đánh bẫy Cache RAM: Nếu đã tạo loại DataType này rồi thì bốc ra xài luôn
        if best_code in KnowledgeService._datatype_cache:
            dt = KnowledgeService._datatype_cache[best_code]
        else:
            # 3. Mapping thông tin hiển thị
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

            # 4. Cập nhật vào Database an toàn
            from apps.app_coach.models import DataType 
            dt, created = DataType.objects.get_or_create(
                code=best_code, 
                defaults={
                    'name': name, 
                    'ai_model_preference': model_pref
                }
            )
            
            if not created and best_code in ["SYSTEM", "SYSTEM_CONFIG", "GUIDE"]:
                dt.name = name
                dt.save(update_fields=['name'])
            
            # Lưu vào bộ nhớ đệm
            KnowledgeService._datatype_cache[best_code] = dt

        draft.data_type = dt
        return dt

    @staticmethod
    def _get_learned_context(project_or_id):
        """
        KẾT NỐI TRI THỨC: Chấp nhận cả Object lẫn ID số nguyên từ tiến trình chạy hàng loạt.
        """
        if isinstance(project_or_id, (int, str)):
            filter_kwargs = {'project_id': project_or_id}
        else:
            filter_kwargs = {'project': project_or_id}

        learned_logs = LearningLog.objects.filter(**filter_kwargs, is_learned=True)
        if not learned_logs.exists():
            return ""
        
        context_parts = ["\n--- 🧠 TRI THỨC HỆ THỐNG ĐÃ HỌC TỪ BAN QUẢN LÝ ---"]
        for log in learned_logs:
            context_parts.append(f"Tình huống: {log.question}\nGiải đáp: {log.admin_answer}")
        
        return "\n\n".join(context_parts) + "\n--- (Hãy áp dụng tri thức trên để phân tích) ---\n"

    @staticmethod
    def _extract_and_log_questions(draft, content):
        """
        BÁO HIỆU HỎI BÀI: Trích xuất góc phản biện để sinh nhật ký học tập.
        """
        if re.search(r'dữ\s+liệu\s+logic\s+đã\s+ổn', content, re.I):
            return False

        pattern = r"\[⚠️\s*(?:GÓC PHẢN BIỆN|Cần xác nhận)\](.*)"
        match = re.search(pattern, content, re.S | re.I)
        
        if match:
            question_content = match.group(1).strip()
            if len(question_content) > 10:
                LearningLog.objects.get_or_create(
                    project=draft.project,
                    question=f"Sheet {draft.sheet.name}: {question_content[:500]}",
                    defaults={'is_learned': False}
                )
                return True
        return False

    @staticmethod
    def _clean_ai_content(text):
        """
        [BỘ LỌC HẬU KỲ] Dọn rác chuyên sâu cho Ollama Qwen 7B & Chuẩn hóa cấu trúc Cloud:
        """
        if not text:
            return ""

        # Lớp 1: Khử lỗi lặp lại cấu trúc tiêu đề (Nếu AI sinh nhiều bộ Mục đích)
        parts = text.split("### 🎯 MỤC ĐÍCH")
        if len(parts) > 2:
            text = "### 🎯 MỤC ĐÍCH" + parts[1]

        # Lớp 2: Xóa các vùng dữ liệu hoặc ô đơn lẻ (Ví dụ: D20:D23, H4, F25, Cell_F15)
        text = re.sub(r'\b[A-Za-z_]{1,3}\d{1,4}(?::[A-Za-z_]{1,3}\d{1,4})?\b', '', text)
        
        # Lớp 3: Xóa tiền tố hệ thống tự chế (Ví dụ: "Ô H4", "ô F25", "Cell_A1")
        text = re.sub(r'\b(Cell_|Ô\s*|ô\s*)[A-Za-z_]{1,3}\d{1,4}\b', '', text)

        # Lớp 4: Xóa sạch các dấu ngoặc rỗng hoặc dấu ngoặc lỗi do sau khi xóa ô Excel bị thừa lại
        text = re.sub(r'\(\s*[,.\s]*\s*\)', '', text)

        # Lớp 5: Chuẩn hóa lại khoảng trắng và ngắt dòng thừa cho tài liệu BA đẹp đẽ
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    @staticmethod
    def refine_draft(draft_or_id, current_idx=1, total=1, external_context=None):
        """
        Xử lý tinh chế chuyên sâu cho single draft. Chấp nhận cả ID lẫn Object nhằm tối ưu RAM.
        Tự động kích hoạt cơ chế nạp Prompt gốc phòng thủ nếu phát hiện DB trống.
        """
        
        from apps.app_ai_core.models import AIPromptConfig
        from apps.app_knowledge.ai_gateway import AIGateway 

        start_time = time.time()
        
        try:
            # 🏎️ KIỂM TRA ĐẦU VÀO: Nếu là ID thì truy vấn, nếu là Object có sẵn từ Batch thì xài luôn!
            if isinstance(draft_or_id, (int, str)):
                draft = KnowledgeDraft.objects.select_related('sheet', 'project', 'data_type').get(id=draft_or_id)
            else:
                draft = draft_or_id

            sheet = draft.sheet
            project = draft.project
            
            print(f"🚀 [AI COACH] {current_idx}/{total} | {sheet.name}")

            # Đảm bảo gán dữ liệu phân loại trước khi bốc tách prompt
            if not draft.data_type_id:
                KnowledgeService.auto_assign_data_type(draft)

            module_slug = draft.data_type.code if draft.data_type else "SYSTEM"

            # 🛡️ LỚP PHÒNG THỦ CHỦ ĐỘNG: Check nhanh nếu chưa có prompt mặc định thì gọi seed ngay lập tức tại runtime
            if not AIPromptConfig.objects.filter(is_default=True).exists():
                try:
                    from apps.app_ai_core.models import seed_default_ai_prompt
                    seed_default_ai_prompt(None)
                except Exception as seed_err:
                    logger.error(f"⚠️ Không thể tự động nạp Prompt phòng thủ: {str(seed_err)}")

            # Tìm Prompt Config theo module nghiệp vụ riêng, nếu không có bốc ngay con mặc định (Vừa được bảo vệ ở trên)
            prompt_config = AIPromptConfig.objects.filter(
                module_code=module_slug, is_active=True
            ).first() or AIPromptConfig.objects.filter(
                is_default=True, is_active=True
            ).first()

            # 🛡️ VÁ LỖI CHỐNG CRASH: Nếu vì lý do hy hữu (bị de-active hết) dẫn tới None, chặn lại ngay
            if not prompt_config:
                logger.error(f"❌ Lỗi: Không tìm thấy cấu hình AIPromptConfig (Active hoặc Default) cho nhóm {module_slug}.")
                draft.status = 'ERROR'
                draft.save(update_fields=['status'])
                return False  # Trả về False an toàn để tiến trình không bị gãy xích

            # Thu thập bối cảnh tri thức đã học được từ các bước trước
            learned_context = external_context if external_context is not None else \
                              KnowledgeService._get_learned_context(project)
            
            # Đọc siêu dữ liệu Excel từ schema cấu trúc của anh
            intel = sheet.metadata or {}
            metadata_str = json.dumps({
                "logic": intel.get("logic_blocks", []), 
                "fields": intel.get("business_data", [])
            }, ensure_ascii=False, indent=2)

            # Đóng gói gói dữ liệu bối cảnh chặt chẽ truyền sang AI
            full_user_content = (
                f"=== BỐI CẢNH HỆ THỐNG ===\n{learned_context}\n\n"
                f"=== NHIỆM VỤ ===\n"
                f"Phân tích nghiệp vụ chi tiết cho danh mục: '{sheet.name}'\n"
                f"Loại dữ liệu: {module_slug}\n\n"
                f"=== METADATA TỪ EXCEL ===\n{metadata_str}"
            )

            final_content = ""
            try:
                # Gọi lớp Gateway điều phối thông minh (Local Ollama / API Cloud)
                ai = AIGateway(config_obj=prompt_config, input_text=full_user_content)
                final_content = ai.run_process()
            except Exception as ai_err:
                # 🛑 BẪY CHÍ MẠNG: Nếu lỗi do cạn kiệt API Key (STOP_BATCH), ném ngược ra ngoài để dừng vòng lặp UI lớn
                if "STOP_BATCH" in str(ai_err):
                    raise ai_err
                
                logger.error(f"❌ AI Error tại {sheet.name}: {str(ai_err)}")
                draft.status = 'ERROR'
                draft.save(update_fields=['status'])
                return False

            if final_content and final_content.strip():
                final_content = KnowledgeService._clean_ai_content(final_content)

                # Bọc cô lập transaction xử lý lưu thông tin kết quả an toàn toàn vẹn dữ liệu
                with transaction.atomic():
                    draft.content = final_content
                    has_questions = KnowledgeService._extract_and_log_questions(draft, final_content)
                    
                    # Nếu có câu hỏi [HỎI_ANH_VŨ], giữ PENDING để anh duyệt, nếu sạch thì sẵn sàng AI_READY
                    draft.status = 'PENDING' if has_questions else 'AI_READY'
                    
                    duration = time.time() - start_time
                    
                    # 🛠️ ĐỒNG BỘ CHUẨN XÁC: Cập nhật fields an toàn và ghi nhận log thời gian xử lý của AI
                    update_fields = ['content', 'status', 'updated_at', 'data_type_id']
                    
                    if hasattr(draft, 'metadata'):
                        meta = draft.metadata or {}
                        meta['ai_processing_time'] = round(duration, 2)
                        draft.metadata = meta
                        update_fields.append('metadata')
                    
                    draft.updated_at = timezone.now()
                    draft.save(update_fields=update_fields)
                
                print(f"✅ Xong: {sheet.name} ({round(duration, 2)}s)")
                return True
            
            return False

        except Exception as e:
            # Nếu lỗi từ Gateway ném ra là STOP_BATCH, dứt khoát đẩy thẳng lên Action ngoài UI ngắt luồng càn quét
            if "STOP_BATCH" in str(e):
                raise e 
            logger.error(f"💥 Lỗi tại Draft {draft_or_id}: {str(e)}", exc_info=True)
            return False
        
    @staticmethod
    def refine_all_project_drafts(project_id, re_process=False):
        """
        CHẠY HÀNG LOẠT 211 NGHIỆP VỤ (Batch Processing Optimized)
        """
        from tqdm import tqdm 

        shared_learned_context = KnowledgeService._get_learned_context(project_id)
        
        draft_query = KnowledgeDraft.objects.filter(project_id=project_id).select_related('sheet', 'data_type')
        if not re_process:
            draft_query = draft_query.exclude(status='AI_READY')

        drafts = list(draft_query)
        total = len(drafts)
        
        if total == 0:
            print(f"✅ Không có nghiệp vụ nào cần tinh chế cho Project {project_id}.")
            return 0

        print(f"\n🚀 [HTJ BATCH] Khởi động chiến dịch càn quét {total} nghiệp vụ...")

        success_count = 0
        fail_count = 0
        start_time = time.time()

        KnowledgeService._datatype_cache.clear()

        # Vòng lặp xử lý chính
        for i, draft in enumerate(tqdm(drafts, desc="Khai thác Miner Excel", unit="sheet")):
            try:
                # 🏎️ TRUYỀN THẲNG INSTANCE 'draft' thay vì truyền ID để loại bỏ hoàn toàn việc truy vấn lặp lại
                status = KnowledgeService.refine_draft(
                    draft, 
                    current_idx=i+1, 
                    total=total,
                    external_context=shared_learned_context 
                )

                if status:
                    success_count += 1
                else:
                    fail_count += 1

                # Quản lý Tần suất gọi API (Rate Limit Protection)
                current_pref = getattr(draft.data_type, 'ai_model_preference', 'OLLAMA')
                if current_pref != 'OLLAMA' and (i + 1) % 10 == 0:
                    time.sleep(2) 

            except Exception as e:
                if "STOP_BATCH" in str(e):
                    print(f"\n🛑 [DỪNG TIẾN TRÌNH] Hết hạn mức API Free ngày hôm nay tại vị trí {i+1}/{total}!")
                    print("Các sheet còn lại được giữ nguyên trạng thái PENDING an toàn để ngày mai chạy tiếp.")
                    break
                
                logger.error(f"❌ Sập cục bộ tại Draft {draft.id}: {str(e)}")
                fail_count += 1
                continue

        duration = round(time.time() - start_time, 2)
        print(f"\n{'='*60}")
        print(f"✨ KẾT QUẢ ĐỢT CÀN QUÉT TRI THỨC Ứng Dụng Vàng")
        print(f"✅ Đã xử lý lưu thành công: {success_count}/{total} sheets")
        print(f"❌ Thất bại: {fail_count} sheets")
        print(f"⏱️ Tổng thời gian chạy máy: {duration} giây")
        print(f"{'='*60}\n")
        
        return success_count