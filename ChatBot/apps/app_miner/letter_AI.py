import json
import re
import tiktoken
import traceback
from django.db import transaction
from .models import ExcelProject, DataField
from apps.app_knowledge.models import KnowledgeDraft, AIPromptTemplate, BusinessLogicRule

class ExcelKnowledgeArchitect:
    def __init__(self):
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

    # --- NHÓM 1: TIỆN ÍCH TỐI ƯU ---
    def _compact_json(self, data):
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def _parse_ai_json(self, text):
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return json.loads(match.group(), strict=False) if match else None
        except: return None

    # --- NHÓM 2: MINING (GOM DỮ LIỆU THÔ) ---
    def collect_terms_to_draft(self, project):
        """Gom thuật ngữ và giữ lại các chỉ số vàng nhạy cảm (610, 750...)"""
        fields = DataField.objects.filter(sheet__project=project).exclude(value="").select_related('sheet')
        
        draft_objs = []
        seen = set()
        gold_keywords = {'610', '750', '999', '9999', '18k', '24k'}

        for f in fields:
            val = str(f.value).strip()
            if not (1 < len(val) < 100) or val in seen: continue

            # Giữ lại nếu không phải số, hoặc là số liên quan đến loại vàng/định danh
            is_num = re.match(r'^-?\d+(?:\.\d+)?$', val)
            parent_col = str(f.metadata.get('area_context', {}).get('parent_col_title', '')).lower()
            
            if not is_num or any(k in val for k in gold_keywords) or any(k in parent_col for k in ['loại', 'tuổi', 'mã']):
                draft_objs.append(KnowledgeDraft(
                    project=project, term=val, category='TERM',
                    sheet_name=f.sheet.name,
                    context=f"Cột: {parent_col} | Ô: {f.cell_address}",
                    status='PENDING'
                ))
                seen.add(val)
        
        if draft_objs:
            with transaction.atomic():
                KnowledgeDraft.objects.bulk_create(draft_objs, ignore_conflicts=True, batch_size=500)
        return len(draft_objs)

    # --- NHÓM 3: ARCHITECT (XÂY DỰNG LOGIC) ---
    def create_logic_drafts_from_formulas(self, project):
        """
        QUAN TRỌNG: Quét các ô có công thức (FORMULA) để tạo bản thảo logic.
        Đây là nền tảng để AI hiểu 'Vàng quy tuổi'.
        """
        formula_fields = DataField.objects.filter(sheet__project=project).exclude(formula="").exclude(formula__isnull=True)
        created_count = 0

        for f in formula_fields:
            title = f"Logic tính toán tại {f.sheet.name}!{f.coordinate}"
            mapping = f.metadata.get('schema_mapping', {})
            
            content = (
                f"Nhãn: {f.label or 'Không tên'}\n"
                f"Công thức Excel: {f.formula}\n"
                f"Liên kết sheet: {', '.join(mapping.get('depends_on_sheets', []))}"
            )

            KnowledgeDraft.objects.get_or_create(
                project=project, title=title,
                defaults={
                    'category': 'LOGIC',
                    'content': content,
                    'status': 'PENDING',
                    'origin_metadata': f.metadata
                }
            )
            created_count += 1
        return created_count

    def _save_extracted_sub_knowledge(self, draft_obj, data):
        """Lưu tự động các Rule/Công thức mà AI bóc tách được"""
        if 'logics' in data and isinstance(data['logics'], list):
            logic_objs = [
                BusinessLogicRule(
                    project=draft_obj.project,
                    rule_name=l.get('name'),
                    formula=l.get('formula', ''),
                    description=l.get('description', '')
                ) for l in data['logics'] if l.get('name')
            ]
            BusinessLogicRule.objects.bulk_create(logic_objs, ignore_conflicts=True)