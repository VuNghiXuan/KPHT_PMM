import json
import re
import tiktoken
import traceback
from django.db import transaction
from django.utils.timezone import now

class ExcelKnowledgeArchitect:
    def __init__(self):
        try:
            # Tối ưu hóa việc đếm token cho model GPT-4o hoặc các LLM hiện đại
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

    def _compact_json(self, data):
        """Giảm tối đa dung lượng JSON để tiết kiệm chi phí AI"""
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def get_token_count(self, data):
        if not self.encoding: return 0
        text = self._compact_json(data) if not isinstance(data, str) else data
        return len(self.encoding.encode(text))

    def collect_terms_to_draft(self, project):
        """
        Gom thuật ngữ thô từ Excel tiệm vàng.
        Tự động lọc các ô rác, chỉ lấy các nhãn có ý nghĩa nghiệp vụ.
        """
        from .models import DataField
        from apps.ai_knowledge.models import KnowledgeDraft

        # Chỉ lấy fields có giá trị, loại bỏ các ô trống
        fields = DataField.objects.filter(sheet__project=project).exclude(value="").select_related('sheet')
        
        draft_objs = []
        seen = set()

        for f in fields:
            val = str(f.value).strip()
            
            # Lọc nhiễu: 
            # 1. Không lấy số thuần túy (tránh lấy nhầm số lượng vàng, tiền)
            # 2. Không lấy từ quá ngắn hoặc quá dài (>100 ký tự thường là đoạn văn, không phải thuật ngữ)
            if (val not in seen and 
                1 < len(val) < 100 and 
                not re.match(r'^-?\d+(?:\.\d+)?$', val)):
                
                ctx = f.metadata.get('area_context', {})
                ui = f.metadata.get('ui_context', {})
                
                draft_objs.append(KnowledgeDraft(
                    project=project, 
                    term=val, 
                    category='TERM', # Gán nhãn là Thuật ngữ
                    sheet_name=f.sheet.name,
                    context=f"Cột: {ctx.get('parent_col_title')} | Vị trí: {f.cell_address}",
                    ui_type=ui.get('type', 'TEXT_INPUT'),
                    status='PENDING'
                ))
                seen.add(val)
        
        # Dùng bulk_create để nạp hàng nghìn ô dữ liệu vào DB trong 1 nốt nhạc
        if draft_objs:
            with transaction.atomic():
                KnowledgeDraft.objects.bulk_create(draft_objs, ignore_conflicts=True, batch_size=500)
        
        return len(draft_objs)

    def create_draft_processes_from_blueprint(self, project):
        """
        Tạo bản thảo quy trình từ cấu trúc Sheet (Ví dụ: Quy trình Bán Vàng, Thu Đổi).
        Tập trung vào các ô có công thức (Formula) để AI học logic tính tiền.
        """
        from apps.ai_knowledge.models import KnowledgeDraft
        from .models import ExcelSheet, DataField

        sheets = ExcelSheet.objects.filter(project=project)
        created_count = 0
        
        for sheet in sheets:
            # Lấy các ô "Sống còn": Nút bấm, Ô nhập liệu quan trọng, và Ô có công thức tính vàng
            fields = DataField.objects.filter(sheet=sheet).filter(
                metadata__ui_context__functional_group__in=[
                    "ACTION_TRIGGER", "CRITICAL_INPUT_VALIDATION", "SECTION_HEADER", "FORMULA_CELL"
                ]
            )
            
            important_elements = []
            for f in fields:
                if f.value and len(str(f.value)) > 1:
                    important_elements.append({
                        "v": f.value,
                        "addr": f.cell_address,
                        "g": f.metadata.get('ui_context', {}).get('functional_group'),
                        "f": f.formula if f.formula else None, # Cực kỳ quan trọng để AI hiểu logic "Vàng quy tuổi"
                        "l": f.metadata.get('business_context', {}).get('labels'),
                    })

            if not important_elements:
                continue

            token_size = self.get_token_count(important_elements)
            
            # Lưu vào bảng KnowledgeDraft với category='PROCESS'
            KnowledgeDraft.objects.update_or_create(
                project=project,
                sheet_name=sheet.name,
                category='PROCESS',
                term=f"Quy trình {sheet.name}",
                defaults={
                    'definition': f"Dữ liệu sẵn sàng ({token_size} tokens). Chờ AI biên soạn quy trình chi tiết.",
                    'logic_mapping': {"ui_context": important_elements},
                    'status': 'PENDING'
                }
            )
            created_count += 1
            
        return created_count

    def call_ai_to_refine(self, draft_obj, template_name="PROCESS_REFINER"):
        """
        Gửi dữ liệu sang AI (GPT/Ollama) để viết lại hướng dẫn sử dụng phần mềm tiệm vàng.
        """
        from apps.ai_knowledge.models import AIPromptTemplate, BusinessLogicRule, KnowledgeDraft
        from apps.ai_knowledge.ai_gateway import AIGateway
        
        try:
            tpl = AIPromptTemplate.objects.filter(name=template_name).first()
            if not tpl:
                return False, f"Thiếu mẫu prompt: {template_name}"

            ui_context = draft_obj.logic_mapping.get("ui_context", [])
            context_str = self._compact_json(ui_context)

            # Ráp dữ liệu vào Prompt
            full_prompt = tpl.template_content.replace("{{context}}", context_str)
            
            ai = AIGateway()
            response_text = ai.process_ai_knowledge(
                full_prompt, 
                system_role=tpl.system_prompt
            )
            
            if not response_text: return False, "AI không phản hồi."

            # Bóc tách JSON từ AI (phòng trường hợp AI trả về có kèm text giải thích)
            data = self._parse_ai_json(response_text)
            if not data:
                return False, "AI trả về dữ liệu lỗi định dạng (Không phải JSON)."

            with transaction.atomic():
                # 1. Cập nhật bản thảo đã tinh chỉnh
                draft_obj.definition = data.get('markdown_content', draft_obj.definition)
                draft_obj.status = 'REVISED'
                draft_obj.save()

                # 2. Nếu AI bóc tách được thuật ngữ con hoặc logic con, lưu luôn vào DB
                self._save_extracted_sub_knowledge(draft_obj, data)

            return True, "Đã tinh chỉnh bản thảo bằng AI thành công."

        except Exception as e:
            print(traceback.format_exc())
            return False, f"Lỗi: {str(e)}"

    def _parse_ai_json(self, text):
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(), strict=False)
            return None
        except:
            return None

    def _save_extracted_sub_knowledge(self, draft_obj, data):
        """Lưu tự động các Rule và Thuật ngữ mà AI phát hiện được trong quá trình đọc Excel"""
        from apps.ai_knowledge.models import KnowledgeDraft, BusinessLogicRule
        
        # Lưu Logic/Công thức tính toán (Ví dụ: Công thức tính bù tiền vàng khách mang tới)
        if 'logics' in data and isinstance(data['logics'], list):
            logic_objs = [
                BusinessLogicRule(
                    project=draft_obj.project,
                    rule_name=l.get('name'),
                    formula=l.get('formula', ''),
                    description=l.get('description', ''),
                    variables=l.get('variables', {})
                ) for l in data['logics'] if l.get('name')
            ]
            BusinessLogicRule.objects.bulk_create(logic_objs, ignore_conflicts=True)

        # Lưu thêm thuật ngữ nếu AI tìm thấy trong ngữ cảnh
        if 'sub_terms' in data and isinstance(data['sub_terms'], list):
            term_objs = [
                KnowledgeDraft(
                    project=draft_obj.project,
                    term=t.get('term'),
                    definition=t.get('definition', ''),
                    category='TERM',
                    sheet_name=draft_obj.sheet_name,
                    status='REVISED'
                ) for t in data['sub_terms'] if t.get('term')
            ]
            KnowledgeDraft.objects.bulk_create(term_objs, ignore_conflicts=True)