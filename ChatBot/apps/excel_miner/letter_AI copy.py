import json
import re
import tiktoken
import datetime
import traceback
from django.db import transaction
from django.utils.timezone import now

class ExcelKnowledgeArchitect:
    def __init__(self):
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

    def _compact_json(self, data):
        """Giảm dung lượng chuỗi JSON để tiết kiệm token"""
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def get_token_count(self, data):
        if not self.encoding: return 0
        text = self._compact_json(data) if not isinstance(data, str) else data
        return len(self.encoding.encode(text))

    def collect_terms_to_draft(self, project):
        """Gom thuật ngữ thô, loại bỏ nhiễu (số, ký tự ngắn)"""
        from .models import DataField
        from apps.ai_knowledge.models import KnowledgeDraft

        # Chỉ lấy fields có giá trị, ưu tiên các field đã được gán nhãn hoặc là Header
        fields = DataField.objects.filter(sheet__project=project).exclude(value="").select_related('sheet')
        
        draft_objs = []
        seen = set()

        for f in fields:
            val = str(f.value).strip()
            # Lọc nhiễu: không lấy số thuần túy, không lấy từ quá ngắn (tránh rác)
            if val not in seen and len(val) > 1 and not re.match(r'^-?\d+(?:\.\d+)?$', val):
                ctx = f.metadata.get('area_context', {})
                ui = f.metadata.get('ui_context', {})
                
                draft_objs.append(KnowledgeDraft(
                    project=project, 
                    term=val, 
                    sheet_name=f.sheet.name,
                    context=f"Cột: {ctx.get('parent_col_title')} | Lân cận: {ctx.get('neighbor_left')}",
                    ui_type=ui.get('type', 'TEXT_INPUT'),
                ))
                seen.add(val)
        
        with transaction.atomic():
            KnowledgeDraft.objects.bulk_create(draft_objs, ignore_conflicts=True, batch_size=500)
        return len(draft_objs)

    def create_draft_processes_from_blueprint(self, project):
        """
        Tạo bản thảo quy trình từ cấu trúc Sheet (Tối ưu Token).
        Sử dụng Model gộp KnowledgeDraft để tránh lỗi Import.
        """
        # IMPORT ĐÚNG MODEL MỚI
        from apps.ai_knowledge.models import KnowledgeDraft
        from .models import ExcelSheet, DataField

        sheets = ExcelSheet.objects.filter(project=project)
        created_count = 0
        
        for sheet in sheets:
            # Chỉ bóc tách các thành phần trọng yếu: Công thức tính vàng, Nút bấm, Validation
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
                        "addr": f.cell_address, # Thêm địa chỉ ô để AI dễ đối chiếu
                        "g": f.metadata.get('ui_context', {}).get('functional_group'),
                        "f": f.formula if f.formula else None, # Giữ công thức để AI hiểu logic 'Vàng quy tuổi'
                        "l": f.metadata.get('business_context', {}).get('labels'),
                    })

            if not important_elements:
                continue

            token_size = self.get_token_count(important_elements)
            
            # SỬ DỤNG KNOWLEDGEDRAFT VỚI CATEGORY='PROCESS'
            KnowledgeDraft.objects.update_or_create(
                project=project,
                sheet_name=sheet.name,
                category='PROCESS', # Đánh dấu đây là Quy trình, không phải Thuật ngữ lẻ
                term=f"Quy trình {sheet.name}", # Tên quy trình
                defaults={
                    'definition': f"Dữ liệu sẵn sàng ({token_size} tokens). Chờ AI biên soạn chi tiết...",
                    'logic_mapping': {"ui_context": important_elements},
                    'status': 'PENDING'
                }
            )
            created_count += 1
            
        return created_count

    def call_ai_with_dynamic_task(self, draft_obj, template_name="USER_GUIDE", is_bulk=False):
        """HÀM TỔNG LỰC: Gọi AI dựa trên Template từ DB"""
        from apps.ai_knowledge.models import AIPromptTemplate, KnowledgeDraft, BusinessLogicRule
        from apps.ai_knowledge.ai_gateway import AIGateway
        
        try:
            tpl = AIPromptTemplate.objects.filter(name=template_name).first() or \
                  AIPromptTemplate.objects.filter(task_type=template_name).first()
            
            if not tpl:
                return False, f"Thiếu mẫu prompt: {template_name}"

            ui_context = draft_obj.logic_mapping.get("ui_context", [])
            context_str = self._compact_json(ui_context)

            # Ráp Prompt & ép JSON
            full_prompt = tpl.template_content.replace("{{context}}", context_str)
            full_prompt += f"\n\nBẮT BUỘC TRẢ VỀ JSON THEO CẤU TRÚC:\n{tpl.json_structure}"

            ai = AIGateway()
            response_text = ai.process_ai_knowledge(
                full_prompt, 
                system_role=tpl.system_prompt, 
                use_ollama=is_bulk
            )
            
            if not response_text: return False, "AI im lặng."

            # Bóc tách JSON an toàn hơn
            data = self._parse_ai_json(response_text)
            if not data:
                return False, "AI trả về dữ liệu không đúng định dạng JSON."

            with transaction.atomic():
                # 1. Cập nhật nội dung chính
                content_key = next((k for k in ['refined_markdown', 'markdown_content', 'content'] if k in data), None)
                if content_key:
                    draft_obj.draft_content = data[content_key]
                
                draft_obj.status = 'REVISED'
                draft_obj.save()

                # 2. Bulk Create Thuật ngữ & Logic để tối ưu DB
                self._save_extracted_knowledge(draft_obj, data)

            return True, f"Thành công: '{tpl.name}'."

        except Exception as e:
            print(traceback.format_exc())
            return False, f"Lỗi hệ thống: {str(e)}"

    def _parse_ai_json(self, text):
        """Helper bóc tách JSON từ phản hồi AI kể cả khi có rác markdown"""
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(), strict=False)
            return None
        except:
            return None

    def _save_extracted_knowledge(self, draft_obj, data):
        """Lưu thuật ngữ và logic theo kiểu Batch"""
        from apps.ai_knowledge.models import KnowledgeDraft, BusinessLogicRule
        
        # Xử lý Thuật ngữ
        if 'terms' in data and isinstance(data['terms'], list):
            terms = [
                KnowledgeDraft(
                    project=draft_obj.project,
                    process_draft=draft_obj,
                    term=t.get('t') or t.get('term'),
                    definition=t.get('d') or t.get('definition', ''),
                    ui_type=t.get('u') or t.get('ui_type', 'TEXT_INPUT'),
                    sheet_name=draft_obj.sheet_name
                ) for t in data['terms'] if (t.get('t') or t.get('term'))
            ]
            KnowledgeDraft.objects.bulk_create(terms, ignore_conflicts=True)

        # Xử lý Logic (ví dụ: công thức bù tiền vàng)
        if 'logics' in data and isinstance(data['logics'], list):
            logics = [
                BusinessLogicRule(
                    process_draft=draft_obj,
                    rule_name=l.get('n') or l.get('name'),
                    formula=l.get('f') or l.get('formula', ''),
                    variables=l.get('v') or l.get('variables', {})
                ) for l in data['logics'] if (l.get('n') or l.get('name'))
            ]
            BusinessLogicRule.objects.bulk_create(logics)