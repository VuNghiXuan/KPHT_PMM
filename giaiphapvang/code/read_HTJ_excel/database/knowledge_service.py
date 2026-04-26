
import json
import requests
import os
import time
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
        self.TOKEN_LIMIT = 8000 

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
        """Gom dữ liệu từ Excel - Đã fix lỗi Class str is not mapped"""
        # print(f"DEBUG: Kiểu dữ liệu nhận được là: {type(sheets_data)}")
        context = []
        
        # Nếu sheets_data trống thì nghỉ khỏe
        if not sheets_data:
            return ""

        # Lấy session để nạp lại dữ liệu nếu cần
        session = self.db.get_session() 
        
        try:
            for s in sheets_data: 
                # KIỂM TRA QUAN TRỌNG: 
                # Nếu s là string (tên sheet) thay vì Object, ta phải query lại hoặc bỏ qua
                if isinstance(s, str):
                    print(f"⚠️ Cảnh báo: sheets_data chứa chuỗi '{s}' thay vì Object. Bỏ qua.")
                    continue
                
                # Nạp lại vào session (chỉ dành cho Object của SQLAlchemy)
                try:
                    session.add(s)
                    # Ép load dữ liệu groups ngay tại đây
                    _ = s.groups 
                except Exception:
                    # Nếu vẫn lỗi add, có thể do s không phải model, ta bỏ qua để ko treo app
                    continue

                context.append(f"--- SHEET: {s.sheet_name} ---")
                for g in s.groups:
                    for f in g.fields:
                        if f.label or f.formula or getattr(f, 'comment', None):
                            info = f"Ô {f.coord}: [{f.label}] = {f.value}"
                            if f.formula: info += f" (Công thức: {f.formula})"
                            if getattr(f, 'comment', None): info += f" | Lưu ý: {f.comment}"
                            context.append(info)
        except Exception as e:
            print(f"❌ Lỗi xử lý context: {e}")
        finally:
            session.close()
            
        return "\n".join(context)

    def draft_business_knowledge(self, sheets_data):
        """
        Hàm điều phối chính: Chia nhỏ từng Sheet để AI xử lý + Tính toán thời gian dự kiến.
        """
        all_results = {"terms": [], "processes": [], "formulas": []}
        total_sheets = len(sheets_data)
        
        if total_sheets == 0:
            return all_results

        # Khởi tạo giao diện Progress trên Streamlit
        progress_text = "🚀 Bắt đầu phân tích dữ liệu..."
        my_bar = st.progress(0, text=progress_text)
        time_info = st.empty() # Chỗ này để ghi thời gian dự kiến
        
        start_time_total = time.time()
        
        for idx, sheet in enumerate(sheets_data):
            current_idx = idx + 1
            sheet_start_time = time.time()
            
            # 1. Lấy context của duy nhất 1 Sheet
            sheet_context = self.prepare_raw_context([sheet]) 
            
            if not sheet_context.strip():
                # Cập nhật tiến độ nếu sheet rỗng
                percent = current_idx / total_sheets
                my_bar.progress(percent, text=f"Bỏ qua sheet trống: {sheet.sheet_name}")
                continue
                
            # 2. Gọi AI xử lý
            print(f"\n🔄 [{current_idx}/{total_sheets}] Đang xử lý: {sheet.sheet_name}...")
            sheet_draft = self._process_chunk_with_ai(sheet_context)
            
            # 3. Gom kết quả
            if sheet_draft:
                all_results["terms"].extend(sheet_draft.get("terms", []))
                all_results["processes"].extend(sheet_draft.get("processes", []))
                all_results["formulas"].extend(sheet_draft.get("formulas", []))
            
            # --- TÍNH TOÁN THỜI GIAN ---
            elapsed_sheet = time.time() - sheet_start_time # Thời gian xong 1 sheet vừa rồi
            avg_time_per_sheet = (time.time() - start_time_total) / current_idx
            remaining_sheets = total_sheets - current_idx
            eta_seconds = avg_time_per_sheet * remaining_sheets
            
            # Định dạng phút:giây
            eta_str = time.strftime("%M:%S", time.gmtime(eta_seconds))
            percent_done = int((current_idx / total_sheets) * 100)
            
            # --- CẬP NHẬT HIỂN THỊ ---
            msg = f"Đang xử lý: {sheet.sheet_name} ({current_idx}/{total_sheets})"
            my_bar.progress(current_idx / total_sheets, text=msg)
            
            # Hiển thị lên UI Streamlit
            time_info.info(f"⏳ **Tiến độ:** {percent_done}% | **Dự kiến còn lại:** ~{eta_str}")
            
            # Print ra console cho anh theo dõi
            print(f"✅ Xong sheet {sheet.sheet_name} trong {elapsed_sheet:.2f}s")
            print(f"📊 Tiến độ: {percent_done}% | Còn lại khoảng: {eta_str}")

        st.success(f"✨ Hoàn thành phân tích {total_sheets} sheets!")
        time_info.empty() # Xóa dòng dự báo khi xong
        return all_results

    def _strip_vector_data(self, data):
        """Lọc bỏ sạch sẽ các mảng số vector để tiết kiệm token"""
        if isinstance(data, dict):
            # Xóa sạch các trường liên quan đến vector hoặc mảng số dài
            return {k: self._strip_vector_data(v) for k, v in data.items() if k not in ['vector', 'embedding']}
        elif isinstance(data, list):
            return [self._strip_vector_data(i) for i in data]
        return data

    def _process_chunk_with_ai(self, chunk_context):
        # 1. LỌC DỮ LIỆU TRƯỚC (Loại bỏ mảng số vector)
        clean_context = self._strip_vector_data(chunk_context)
        
        prompt = f"""
        Bạn là chuyên gia BA hệ thống vàng bạc HTJ. 
        Hãy trích xuất: Thuật ngữ (term), Quy trình (process), Công thức (formula).
        DỮ LIỆU:
        {clean_context}
        
        YÊU CẦU: Trả về JSON duy nhất. Nếu không có dữ liệu nghiệp vụ, trả về các list rỗng. 
        Định dạng JSON: {{"terms": [{{ "term": "...", "definition": "..." }}], "processes": [], "formulas": []}}
        """

        # --- 🔵 IN ĐẦU VÀO (INPUT) GỬI CHO AI ---
        print("\n" + "="*50)
        print("📤 [INPUT] GỬI DỮ LIỆU CHO AI:")
        # In 500 ký tự đầu của prompt để anh check xem context có sạch không (tránh tràn console)
        print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        print("="*50)

        try:
            # Gọi API
            response = self._call_ai_api(prompt)
            
            # --- 🟢 IN ĐẦU RA (OUTPUT) TỪ AI TRẢ VỀ ---
            print("\n--- 🤖 [OUTPUT] AI PHẢN HỒI NGUYÊN BẢN ---")
            print(response) 
            print("-" * 40 + "\n")
            
            # 2. XỬ LÝ JSON
            # Làm sạch nếu AI trả về có kèm Markdown ```json ... ```
            clean_json = re.sub(r'```json\s*|```', '', response).strip()
            
            # Tìm vị trí thực sự của JSON
            start_idx = clean_json.find('{')
            end_idx = clean_json.rfind('}') + 1
            
            if start_idx == -1:
                print("⚠️ Cảnh báo: AI không trả về đúng định dạng JSON.")
                return {"terms": [], "processes": [], "formulas": []}

            final_json = json.loads(clean_json[start_idx:end_idx])
            
            # In tóm tắt kết quả sau khi parse thành công
            print(f"✅ Đã trích xuất: {len(final_json.get('terms', []))} thuật ngữ, "
                  f"{len(final_json.get('processes', []))} quy trình.")
            
            return final_json

        except Exception as e:
            print(f"❌ Lỗi xử lý tại AI: {str(e)}")
            return {"terms": [], "processes": [], "formulas": []}
        

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


    def _process_chunk_with_ai(self, chunk_context):
        """
        Hàm phụ: Chỉ lo việc gửi 1 đoạn context cho AI và parse JSON.
        Đảm bảo hàm này nằm bên trong class KnowledgeService.
        """
        prompt = f"""
        Bạn là chuyên gia BA cho hệ thống vàng bạc HTJ. 
        Hãy trích xuất thuật ngữ, quy trình và công thức từ dữ liệu này.
        DỮ LIỆU:
        {chunk_context}
        
        YÊU CẦU: Trả về JSON (terms, processes, formulas). 
        Nếu không có dữ liệu nghiệp vụ, trả về các list rỗng. Chỉ trả về JSON.
        """
        try:
            # Gọi hàm API của anh
            response = self._call_ai_api(prompt)
            
            # Làm sạch JSON (Khử markdown ```json ...)
            import re
            import json
            clean_json = re.sub(r'```json\s*|```', '', response).strip()
            
            # Tìm cặp dấu ngoặc nhọn thực sự
            start_idx = clean_json.find('{')
            end_idx = clean_json.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                clean_json = clean_json[start_idx:end_idx]
            
            return json.loads(clean_json)
        except Exception as e:
            print(f"❌ Lỗi xử lý chunk tại AI: {e}")
            return {"terms": [], "processes": [], "formulas": []}
        

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