# File: D:\ThanhVu\kpht\KPHT_PMM\ChatBot\apps\excel_miner\letter_AI.py

import json
import re
import tiktoken
import datetime
import traceback
from django.db import transaction

class ExcelKnowledgeArchitect:
    def __init__(self):
        # Sử dụng encoding cl100k_base phù hợp cho GPT-3.5/4 hoặc Ollama/LangChain
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback nếu không có internet hoặc lỗi thư viện
            self.encoding = None

    def get_token_count(self, data):
        """Tính toán số lượng token để kiểm soát ngữ cảnh gửi lên AI"""
        if not self.encoding:
            return 0
        text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
        return len(self.encoding.encode(text))

    def collect_terms_to_draft(self, project):
        """
        Gom dữ liệu thô từ DataField vào BusinessTermDraft.
        """
        # LOCAL IMPORT: Tránh lỗi Circular Import
        from .models import DataField
        from apps.ai_knowledge.models import BusinessTermDraft

        fields = DataField.objects.filter(sheet__project=project).exclude(value="")
        draft_objs = []
        seen = set()

        for f in fields:
            val = str(f.value).strip()
            # Lọc: Độ dài > 1, không phải thuần số, chưa xuất hiện trong danh sách quét
            if val not in seen and len(val) > 1 and not val.replace('.', '').isdigit():
                ctx = f.metadata.get('area_context', {})
                ui = f.metadata.get('ui_context', {})
                
                draft_objs.append(BusinessTermDraft(
                    project=project, 
                    term=val, 
                    sheet_name=f.sheet.name,
                    context=f"Cột: {ctx.get('parent_col_title')} | Trái: {ctx.get('neighbor_left')}",
                    ui_type=ui.get('type'),
                ))
                seen.add(val)
        
        # Sử dụng ignore_conflicts để tránh lỗi nếu trùng Unique trong lúc bulk_create
        BusinessTermDraft.objects.bulk_create(draft_objs, ignore_conflicts=True)
        return len(draft_objs)

    def generate_system_blueprint(self, project):
        """Tạo cấu trúc JSON mô tả 'xương sống' của file Excel cho AI"""
        # LOCAL IMPORT
        from .models import ExcelSheet, DataField

        sheets = ExcelSheet.objects.filter(project=project)
        system_map = {
            "project_info": {
                "name": project.name,
                "scanned_at": datetime.datetime.now().isoformat()
            },
            "structure": []
        }

        for sheet in sheets:
            fields = DataField.objects.filter(sheet=sheet)
            sheet_structure = {"sheet_name": sheet.name, "elements": []}
            
            for f in fields:
                if f.value or f.formula:
                    sheet_structure["elements"].append({
                        "address": f.cell_address, 
                        "val": f.value, 
                        "formula": f.formula,
                        "type": f.metadata.get('ui_context', {}).get('type'),
                        "group": f.metadata.get('ui_context', {}).get('functional_group'),
                        "labels": f.metadata.get('business_context', {}).get('labels')
                    })
            system_map["structure"].append(sheet_structure)

        return system_map

    def create_draft_processes_from_blueprint(self, project):
        """
        BƯỚC 1: Xử lý theo từng Sheet (Sheet-level Chunking)
        """
        from apps.ai_knowledge.models import BusinessProcessDraft
        from .models import ExcelSheet, DataField

        sheets = ExcelSheet.objects.filter(project=project)
        
        for sheet in sheets:
            # Chỉ lấy các field quan trọng của RIÊNG sheet này
            fields = DataField.objects.filter(sheet=sheet)
            
            # Chắt lọc dữ liệu để giảm token (Chỉ lấy field có nghiệp vụ)
            important_elements = []
            for f in fields:
                group = f.metadata.get('ui_context', {}).get('functional_group')
                if group in ["ACTION_TRIGGER", "CRITICAL_INPUT_VALIDATION", "SECTION_HEADER"]:
                    if f.value and len(str(f.value)) > 1:
                        important_elements.append({
                            "v": f.value,
                            "g": group,
                            "a": f.cell_address,
                            "f": f.formula,
                            "l": f.metadata.get('business_context', {}).get('labels'),
                            "cmt": f.metadata.get('ui_context', {}).get('comment') # Vét thêm comment ở đây
                        })

            if len(important_elements) < 2:
                continue

            # Kiểm soát token cục bộ cho từng sheet
            sheet_token_count = self.get_token_count(important_elements)
            
            # Nếu 1 sheet vẫn quá lớn (> 4000 token), ta có thể chunk tiếp theo group
            # Nhưng với file Excel tiệm vàng thường 1 sheet sẽ không quá mức này.
            
            BusinessProcessDraft.objects.update_or_create(
                project=project,
                sheet_name=sheet.name,
                defaults={
                    'process_name': f"Quy trình {sheet.name}",
                    'draft_content': f"Chờ thực thi (Dung lượng: {sheet_token_count} tokens)",
                    'logic_mapping': {"ui_context": important_elements},
                    'status': 'PENDING'
                }
            )

    def call_ai_to_write_process(self, draft_obj):
        """
        HÀM SIÊU CẤP: Chuyển đổi logic Excel thành hướng dẫn sử dụng Web App thực tế.
        Ép AI đóng vai chuyên gia đào tạo nhân viên tiệm vàng.
        """
        from apps.ai_knowledge.ai_gateway import AIGateway
        from apps.ai_knowledge.models import BusinessTermDraft, BusinessLogicRule
        import json
        import re
        from django.db import transaction

        ai = AIGateway()
        ui_context = draft_obj.logic_mapping.get("ui_context", [])
        
        if not ui_context:
            return False, "Không tìm thấy ngữ cảnh UI (vị trí ô Excel)."

        # Prompt nâng cấp: Chú trọng vào việc mô tả giao diện Web từ dữ liệu Excel
        # Prompt NÂNG CẤP: Ép AI tập trung vào Markdown trước, bóc tách sau
        # Prompt NÂNG CẤP: Sử dụng thuật ngữ Web App (Tab, Popup, Grid, Button)
        prompt = (
            f"Bạn là chuyên gia đào tạo nhân viên cho phần mềm quản lý tiệm vàng Ứng Dụng Vàng.\n"
            f"Nhiệm vụ: Viết hướng dẫn sử dụng giao diện Web App dựa trên sơ đồ Excel '{draft_obj.sheet_name}'.\n"
            f"Dữ liệu thực tế: {json.dumps(ui_context, ensure_ascii=False)}.\n\n"

            f"--- QUY TẮC NGÔN NGỮ (BẮT BUỘC) ---\n"
            f"1. KHÔNG DÙNG: 'ô Excel', 'phía trên/dưới', 'nhìn vào ô'.\n"
            f"2. PHẢI DÙNG các thuật ngữ sau để mô tả:\n"
            f"   - 'Popup/Form nhập liệu': Khi nói về cửa sổ thêm mới hoặc chỉnh sửa.\n"
            f"   - 'Grid/Bảng danh sách': Khi nói về danh sách các hàng hóa hoặc danh sách phiếu.\n"
            f"   - 'Tab/Thanh điều hướng': Khi nói về các phân mục chính.\n"
            f"   - 'Nút bấm (Button)': Khi nói về các hành động Lưu, Duyệt, In, Hủy.\n"
            f"   - 'Trường dữ liệu (Field)': Khi nói về các chỗ nhập Tên, SĐT, Mã phiếu.\n\n"

            f"--- CẤU TRÚC NỘI DUNG HƯỚNG DẪN (markdown_content) ---\n"
            f"Hãy viết một bài hướng dẫn chi tiết (ít nhất 500 chữ) chia làm các giai đoạn:\n"
            f"   - Bước 1: Thao tác trên Grid danh sách. Nhấn nút 'Thêm' (ô W2) để mở Popup nhập liệu.\n"
            f"   - Bước 2: Tại Form nhập liệu, điền 'Thông tin chung' và 'Thông tin NCC'. Nhấn mạnh việc kiểm tra SĐT và Mã chứng từ.\n"
            f"   - Bước 3: Nhập liệu tại Grid chi tiết hàng hóa. Giải thích cách dòng dữ liệu tự động tính toán VAT và Thành tiền.\n"
            f"   - Bước 4: Kiểm tra các trường tổng kết (Thanh toán, Còn lại) và nhấn nút 'Lưu' hoặc 'Tạo phiếu chi'.\n\n"

            f"--- GIẢI THÍCH LOGIC NGHIỆP VỤ ---\n"
            f"Dựa vào các công thức như =SUM(K23:K25), hãy giải thích bằng tiếng Việt bình dân: 'Hệ thống tự cộng dồn tổng tiền của tất cả các món hàng trong bảng'.\n\n"

            f"TRẢ VỀ JSON THEO MẪU:\n"
            f"{{\n"
            f"  \"markdown_content\": \"# 📗 HƯỚNG DẪN CHI TIẾT: [Tên nghiệp vụ]\\n\\n### 1. Khởi tạo phiếu\\nTại **Grid danh sách**, nhấn nút...\",\n"
            f"  \"terms\": [{{ \"t\": \"Grid chi tiết\", \"d\": \"Bảng hiển thị danh sách hàng hóa trong phiếu\", \"u\": \"GRID\" }}],\n"
            f"  \"logics\": [{{ \"n\": \"Tổng thanh toán\", \"f\": \"Tổng tiền hàng sau thuế + Nợ cũ\", \"v\": \"C30\" }}]\n"
            f"}}\n"
        )
        try:
            response_text = ai.process_ai_knowledge(prompt)
            
            # Xử lý bóc tách JSON từ phản hồi của AI
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            content = json_match.group(1) if json_match else response_text[response_text.find('{'):response_text.rfind('}') + 1]

            data = json.loads(content, strict=False)

            with transaction.atomic():
                # 1. Cập nhật nội dung hướng dẫn
                draft_obj.draft_content = data.get('markdown_content', '')
                draft_obj.status = 'REVISED'
                draft_obj.save()

                # 2. Bóc tách Thuật ngữ (Chuyển từ Excel sang khái niệm Web)
                term_objs = []
                for t in data.get('terms', []):
                    term_objs.append(BusinessTermDraft(
                        project=draft_obj.project,
                        process_draft=draft_obj,
                        term=t.get('t'),
                        definition=t.get('d'),
                        ui_type=t.get('u', 'TEXT_INPUT'),
                        sheet_name=draft_obj.sheet_name,
                        status='PENDING'
                    ))
                if term_objs:
                    BusinessTermDraft.objects.bulk_create(term_objs, ignore_conflicts=True)

                # 3. Bóc tách Logic (Diễn giải phép tính)
                logic_objs = []
                for l in data.get('logics', []):
                    logic_objs.append(BusinessLogicRule(
                        process_draft=draft_obj,
                        rule_name=l.get('n'),
                        formula=l.get('f'),
                        variables=l.get('v')
                    ))
                if logic_objs:
                    BusinessLogicRule.objects.bulk_create(logic_objs)

            return True, f"Thành công! Đã tạo hướng dẫn web, bóc được {len(term_objs)} thuật ngữ."
            
        except Exception as e:
            return False, f"Lỗi xử lý dữ liệu AI: {str(e)}"
    
    def approve_and_extract_terms(self, draft_obj):
        """
        NÂNG CẤP: Phê duyệt một phát đẩy hết từ Draft sang Official.
        """
        from apps.ai_knowledge.models import BusinessProcess, BusinessTerm
        
        try:
            with transaction.atomic():
                # 1. Chuyển Quy trình sang chính thức
                official_proc, _ = BusinessProcess.objects.update_or_create(
                    name=draft_obj.process_name,
                    defaults={
                        'description': draft_obj.draft_content,
                        'logic_rules': f"Sheet: {draft_obj.sheet_name}"
                    }
                )

                # 2. Chuyển các thuật ngữ liên quan sang chính thức
                related_terms = draft_obj.related_terms.filter(status='PENDING')
                for dt in related_terms:
                    BusinessTerm.objects.update_or_create(
                        term=dt.term,
                        defaults={
                            'definition': dt.definition,
                            'project': dt.project,
                            'source_field': None # Có thể map lại sau
                        }
                    )
                    dt.status = 'DONE'
                    dt.save()

                draft_obj.status = 'APPROVED'
                draft_obj.save()
                return True, "Đã chuyển toàn bộ tri thức sang bộ nhớ chính thức."
                
        except Exception as e:
            return False, f"Lỗi phê duyệt: {str(e)}"
    
    # Hàm hỗ trợ tinh chỉnh lại nội dung quy trình sau khi đã được gọt dũa (Sau AI biên soạn--> gọt dũa--> AI soạn lại)

    def refine_ai_process(self, draft_obj):
        """
        Dành riêng cho việc tinh chỉnh nội dung anh Vũ đã sửa tay.
        """
        from apps.ai_knowledge.ai_gateway import AIGateway
        import json

        ai = AIGateway()
        
        # Lấy nội dung hiện tại anh Vũ đang sửa trong TextField
        current_content = draft_obj.draft_content
        ui_context = draft_obj.logic_mapping.get("ui_context", [])

        # PROMPT BIÊN TẬP VIÊN (Khác hoàn toàn với prompt bóc tách gốc)
        # PROMPT BIÊN TẬP VIÊN ĐÃ TỐI ƯU THEO Ý ANH VŨ
        prompt = (
            f"Bạn là biên tập viên kỹ thuật cao cấp cho hệ thống phần mềm Ứng Dụng Vàng.\n"
            f"Nhiệm vụ: Chỉnh sửa bản hướng dẫn cho form '{draft_obj.sheet_name}' để đào tạo nhân viên.\n\n"
            
            f"--- DỮ LIỆU ĐỐI CHIẾU (UI CONTEXT) ---\n"
            f"{json.dumps(ui_context, ensure_ascii=False)}\n\n"

            f"--- NỘI DUNG ĐANG VIẾT (CẦN SỬA) ---\n"
            f"{current_content}\n\n"
            
            f"--- QUY TẮC BIÊN TẬP BẮT BUỘC ---\n"
            f"1. MỤC ĐÍCH NGHIỆP VỤ: Luôn bắt đầu bằng mục '1. Mục đích' để giải thích form này dùng làm gì trong quản lý vàng.\n"
            
            f"2. CẤM TUYỆT ĐỐI CÔNG THỨC EXCEL: Đây là lỗi nghiêm trọng nhất. \n"
            f"   - KHÔNG ĐƯỢC PHÉP xuất hiện các ký tự: '=', 'H19', 'G19', 'SUM', 'I19:I21'...\n"
            f"   - CÁCH SỬA: Dựa vào logic Excel đó, hãy viết lại thành câu tiếng Việt. \n"
            f"     Ví dụ: '=H19*G19' phải viết là 'Hệ thống tự tính: [Số lượng] x [Đơn giá]'.\n"
            f"     Ví dụ: '=SUM(...)' phải viết là 'Tổng cộng toàn bộ danh sách hàng'.\n"
            
            f"3. ĐỊNH DẠNG: Giữ nguyên cấu trúc Markdown (###, **). \n"
            f"4. ĐỐI TƯỢNG ĐỌC: Là nhân viên bán vàng, không phải dân IT, nên ngôn ngữ phải bình dân, chuyên nghiệp.\n\n"

            f"TRẢ VỀ JSON DUY NHẤT:\n"
            f"{{\n"
            f"  \"refined_markdown\": \"(Nội dung đã 'sạch' công thức Excel và có thêm mục đích)\"\n"
            f"}}\n"
        )
        try:
            response_text = ai.process_ai_knowledge(prompt)
            # Logic bóc tách JSON từ Response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                # CẬP NHẬT LẠI VÀO DRAFT
                draft_obj.draft_content = data.get('refined_markdown', current_content)
                draft_obj.save()
                return True, "AI đã biên tập lại quy trình theo bản sửa tay của anh."
            return False, "Không thể bóc tách JSON từ phản hồi của AI."
        except Exception as e:
            return False, f"Lỗi AI: {str(e)}"
