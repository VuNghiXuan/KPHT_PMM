import json
import requests
import os
import re
import logging
import streamlit as st
import tiktoken
from sqlalchemy import or_
from database.models import VectorKnowledge

class KnowledgeService:
    def __init__(self, db_manager, kv_manager, ai_agent=None):
        self.db = db_manager
        self.kv = kv_manager # Lưu lại để dùng cho export/import
        self.ai_agent = ai_agent
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.TOKEN_LIMIT = 4000 

    # --- PHẦN 1: GIAO TIẾP AI (CỐT LÕI) ---

    def _call_ai_api(self, prompt):
        """Hàm điều phối: Kiểm tra Token trước, chọn Provider sau"""
        
        # 1. KIỂM TRA TOKEN TRƯỚC
        token_count = len(self.encoder.encode(prompt))
        
        # Lấy cấu hình ưu tiên từ .env
        preferred_provider = os.getenv("AI_PROVIDER", "groq").lower()
        
        # 2. LOGIC QUYẾT ĐỊNH PROVIDER
        if token_count > self.TOKEN_LIMIT:
            actual_provider = "ollama"
            print(f"⚠️ Nội dung quá dài ({token_count} tokens) -> Bắt buộc dùng OLLAMA")
        else:
            actual_provider = preferred_provider
            print(f"🚀 Token ổn ({token_count}) -> Dùng {actual_provider.upper()}")

        # 3. THỰC THI GỌI API THEO PROVIDER ĐÃ CHỌN
        try:
            if actual_provider == "groq":
                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    temperature=0.1
                )
                return completion.choices[0].message.content

            elif actual_provider == "gemini":
                from google import genai
                client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
                response = client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                    contents=prompt
                )
                return response.text

            else:  # Mặc định là OLLAMA (Local)
                base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
                payload = {
                    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                response = requests.post(f"{base_url}/api/generate", json=payload, timeout=300)
                return response.json().get("response", "")

        except Exception as e:
            return f"❌ Lỗi tại bộ não {actual_provider}: {str(e)}"

    # --- PHẦN 2: BIÊN SOẠN TRI THỨC (DRAFTING) ---

    def prepare_raw_context(self, sheets_data):
        """Gom dữ liệu 'có hồn' từ Excel (nhãn, công thức, comment)"""
        context = []
        for s in sheets_data:
            context.append(f"--- SHEET: {s.sheet_name} ---")
            for g in s.groups:
                for f in g.fields:
                    if f.label or f.formula or getattr(f, 'comment', None):
                        info = f"Ô {f.coord}: [{f.label}] = {f.value}"
                        if f.formula: info += f" (Công thức: {f.formula})"
                        if getattr(f, 'comment', None): info += f" | Lưu ý: {f.comment}"
                        context.append(info)
        return "\n".join(context)

    def draft_business_knowledge(self, sheets_data):
        """
        Hàm chính để AI biên soạn nháp tri thức nghiệp vụ.
        Tự động phân loại (Category) và trích xuất logic công thức từ dữ liệu Excel.
        """
        # 1. Chuẩn bị ngữ cảnh từ dữ liệu thô (đã fix lỗi 'str' object ở bước trước)
        raw_context = self.prepare_raw_context(sheets_data)
        
        if not raw_context:
            return {"terms": [], "processes": [], "formulas": []}

        # 2. Xây dựng Prompt "thông minh" với yêu cầu phân loại tự động
        prompt = f"""
        Bạn là chuyên gia phân tích nghiệp vụ (BA) cấp cao cho hệ thống quản lý vàng bạc đá quý HTJ Jewelry.
        Nhiệm vụ: Đọc dữ liệu thô từ Excel và hệ thống hóa thành 'Bộ não tri thức'.

        DỮ LIỆU EXCEL THÔ:
        ---
        {raw_context}
        ---

        YÊU CẦU TRÍCH XUẤT (TRẢ VỀ JSON DUY NHẤT):
        1. 'terms': Các thuật ngữ nghiệp vụ. 
        - 'category': Tự động phân loại dựa trên nội dung (VÀNG, CÔNG NỢ, KẾ TOÁN, HỆ THỐNG).
        2. 'processes': Các quy trình tính toán hoặc luồng công việc.
        3. 'formulas': Các công thức tính toán đặc thù (VD: Công thức tính tuổi vàng, tiền công).

        CẤU TRÚC JSON MẪU:
        {{
            "terms": [
                {{
                    "term": "Tên thuật ngữ",
                    "definition": "Định nghĩa chi tiết và cách sử dụng",
                    "category": "VÀNG"
                }}
            ],
            "processes": [
                {{
                    "name": "Quy trình đổi vàng",
                    "steps": "Bước 1... Bước 2...",
                    "logic_rules": "Luật bù trừ độ tinh khiết"
                }}
            ],
            "formulas": [
                {{
                    "name": "Tính giá vốn",
                    "explanation": "Giá vàng nguyên liệu + Tiền công + Đá gắn kèm"
                }}
            ]
        }}
        Lưu ý: Chỉ trả về JSON, không giải thích gì thêm.
        """

        try:
            # 3. Gọi API AI (Hàm _call_ai_api của anh)
            response = self._call_ai_api(prompt)
            
            # 4. Xử lý làm sạch phản hồi từ AI
            # Khử markdown nếu AI trả về dạng ```json ... ```
            clean_json = re.sub(r'```json\s*|```', '', response).strip()
            
            # Tìm vị trí JSON thực sự (phòng trường hợp AI nói nhảm ở đầu/cuối)
            start_idx = clean_json.find('{')
            end_idx = clean_json.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                clean_json = clean_json[start_idx:end_idx]

            data = json.loads(clean_json)
            
            # 5. Hậu xử lý: Đảm bảo các key quan trọng luôn tồn tại để không lỗi View
            if 'terms' not in data: data['terms'] = []
            if 'processes' not in data: data['processes'] = []
            if 'formulas' not in data: data['formulas'] = []
            
            # Chuẩn hóa Category thành chữ in hoa
            for t in data['terms']:
                t['category'] = t.get('category', 'KHÁC').upper()
                
            return data

        except json.JSONDecodeError as je:
            logging.error(f"❌ Lỗi Parse JSON từ AI: {je}")
            return {"error": "AI trả về định dạng không hợp lệ", "raw": response}
        except Exception as e:
            logging.error(f"❌ Lỗi không xác định khi gọi AI: {e}")
            return {"error": str(e)}

    # --- PHẦN 3: LƯU TRỮ & DUYỆT (DATABASE) ---

    def approve_and_learn(self, draft_results):
        """Lưu tri thức đã duyệt vào VectorKnowledge"""
        session = self.db.get_session()
        try:
            # Lưu thuật ngữ
            for item in draft_results.get('terms', []):
                existing = session.query(VectorKnowledge).filter_by(main_term=item['term']).first()
                if existing:
                    existing.definition = item['definition']
                else:
                    session.add(VectorKnowledge(
                        main_term=item['term'],
                        definition=item['definition'],
                        category=item.get('category', 'VÀNG')
                    ))
            
            # Lưu quy trình vào logic_rules của thuật ngữ liên quan (hoặc bảng riêng tùy anh)
            # Ở đây tui lưu tạm vào log để anh theo dõi
            print(f"✅ Đã xử lý {len(draft_results.get('terms', []))} thuật ngữ.")
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi lưu DB: {e}")
            return False
        finally:
            session.close()