import streamlit as st
import pandas as pd
import time
import os
import json
import re
from config import Config

class KnowledgeView:
    def __init__(self, knowledge_service):
        self.service = knowledge_service

    def render_approval_interface(self, project_id, project_name="Dự án hiện tại"):
        st.subheader(f"🧠 Từ điển nghiệp vụ: {project_name}")

        # --- BƯỚC 1: TỰ ĐỘNG LẤY DỮ LIỆU ĐÃ CÓ TRONG DB ---
        with self.service.db.get_session() as session:
            from database.models import VectorKnowledge, ExcelSheet
            # 1. Lấy tri thức đã tốt nghiệp (đã có định nghĩa)
            existing_knowledge = session.query(VectorKnowledge).all()
            # 2. Lấy toàn bộ nhãn thô từ Excel để so soát
            sheets_data = session.query(ExcelSheet).filter_by(project_id=project_id).all()

        # Tạo danh sách các từ đã biết để loại trừ
        known_terms = {k.main_term for k in existing_knowledge if k.definition}

        # --- BƯỚC 2: HIỂN THỊ TRI THỨC HIỆN TẠI ---
        with st.expander("📚 Thư viện tri thức hiện có", expanded=not bool(st.session_state.get('df_knowledge'))):
            if existing_knowledge:
                existing_df = pd.DataFrame([{
                    "term": k.main_term,
                    "definition": k.definition,
                    "category": k.category
                } for k in existing_knowledge])
                st.dataframe(existing_df, width='stretch', hide_index=True)
            else:
                st.info("Chưa có tri thức nào được nạp. Hãy quét Excel bên dưới.")

        st.divider()

        # --- BƯỚC 3: QUÉT VÀ ĐỊNH NGHĨA MỚI ---
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("#### 🔍 Phát hiện thuật ngữ mới")
        with col2:
            # Nút bấm để kích hoạt quét thô và gọi AI
            if st.button("✨ Quét & Gọi AI định nghĩa mới", width='stretch', type="primary"):
                with st.status("Đang đối soát và gọi AI...", expanded=True) as status:
                    # 1. Chuẩn bị context thô
                    raw_context = self.service.prepare_raw_context(sheets_data)
                    
                    # 2. Gọi AI soạn thảo (Hàm này tự chọn Groq/Ollama dựa trên token)
                    draft_data = self.service.draft_business_knowledge(raw_context)
                    
                    if draft_data and 'terms' in draft_data:
                        # 3. Lọc bỏ những từ AI vừa soạn mà thực ra trong DB ĐÃ CÓ RỒI
                        new_terms_only = [
                            t for t in draft_data['terms'] 
                            if t['term'] not in known_terms
                        ]
                        
                        if new_terms_only:
                            df = pd.DataFrame(new_terms_only)
                            df['is_approved'] = False
                            st.session_state.df_knowledge = df
                            status.update(label=f"✅ Tìm thấy {len(df)} thuật ngữ mới!", state="complete")
                        else:
                            status.update(label="✅ Không có thuật ngữ mới nào cần định nghĩa.", state="complete")
                    else:
                        st.error("AI không trích xuất được dữ liệu.")

        # --- BƯỚC 4: BẢNG DUYỆT TỪ MỚI (CHỈ HIỆN KHI CÓ TỪ MỚI) ---
        if 'df_knowledge' in st.session_state and not st.session_state.df_knowledge.empty:
            st.warning("⚠️ Những mục dưới đây là AI gợi ý từ file Excel, anh Vũ hãy duyệt để nạp vào bộ não:")
            
            edited_df = st.data_editor(
                st.session_state.df_knowledge,
                column_config={
                    "term": st.column_config.TextColumn("Thuật ngữ mới", disabled=True),
                    "definition": st.column_config.TextColumn("AI Gợi ý định nghĩa (Sửa nếu cần)", width="large"),
                    "is_approved": st.column_config.CheckboxColumn("Nạp?")
                },
                hide_index=True, width='stretch', key="new_term_editor"
            )

            if st.button("🚀 XÁC NHẬN NẠP THÊM TRI THỨC", width='stretch'):
                to_save = edited_df[edited_df["is_approved"] == True]
                if not to_save.empty:
                    if self.service.approve_and_learn({"terms": to_save.to_dict(orient='records')}):
                        st.success("✅ Đã cập nhật bộ não thành công!")
                        del st.session_state.df_knowledge
                        st.rerun()

    def render_backup_tools(self, project_id):
        """Công cụ Export/Import JSON để anh cất file vật lý"""
        st.divider()
        st.subheader("💾 Backup & Đồng bộ File JSON")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Xuất JSON (Cập nhật mới nhất)", width='stretch'):
                with self.service.db.get_session() as session:
                    # Giả sử hàm export nằm trong kv_manager hoặc service
                    success, path, count = self.service.db.export_knowledge_to_json(project_id)
                    if success:
                        st.success(f"Đã lưu {count} tri thức vào: {path}")

        with col2:
            if st.button("📥 Nhập JSON vào Hệ thống", width='stretch'):
                # Logic import từ file vật lý ngược lại DB
                st.info("Tính năng đang đồng bộ...")