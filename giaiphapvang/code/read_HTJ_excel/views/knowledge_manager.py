import streamlit as st
import pandas as pd
import time
import os
import json
import re
from config import Config
from database.models import VectorKnowledge, ExcelSheet

class KnowledgeView:
    def __init__(self, knowledge_service):
        self.service = knowledge_service

    #-------------------------------------------------------------
    # 1 Hiển thị kết quả bức thư AI
    #-------------------------------------------------------------
    def _handle_ai_scan(self, sheets_data, known_terms):
        """Hàm xử lý quét Excel và gọi AI định nghĩa"""
        with st.status("Đang đối soát và gọi AI...", expanded=True) as status:
            # Test 10 sheet đầu như anh yêu cầu
            print('Test 10 sheet đầu -------------------------------------------')
            draft_data = self.service.draft_business_knowledge(sheets_data[:10]) 
            
            if not draft_data or 'terms' not in draft_data:
                st.error("AI không trích xuất được dữ liệu.")
                return

            new_terms_only = []
            for t in draft_data['terms']:
                # Chuẩn hóa dữ liệu từ AI (Dict hoặc Str)
                term_name = t['term'] if isinstance(t, dict) else t
                if term_name not in known_terms:
                    new_terms_only.append({
                        "term": term_name,
                        "definition": t.get('definition', "AI chưa định nghĩa...") if isinstance(t, dict) else "Chưa có định nghĩa",
                        "category": t.get('category', "PENDING") if isinstance(t, dict) else "PENDING",
                        "is_approved": False
                    })

            if new_terms_only:
                st.session_state.df_knowledge = pd.DataFrame(new_terms_only)
                status.update(label=f"✅ Tìm thấy {len(new_terms_only)} thuật ngữ mới!", state="complete")
            else:
                status.update(label="✅ Không có thuật ngữ mới nào.", state="complete")

    def _render_knowledge_editor(self):
        """Hàm hiển thị bảng GUI để chỉnh sửa và duyệt trực tiếp"""
        if 'df_knowledge' not in st.session_state or st.session_state.df_knowledge.empty:
            return

        st.warning("⚠️ Những mục dưới đây là AI gợi ý, anh Vũ hãy duyệt để nạp vào bộ não:")
        
        # Bảng chỉnh sửa trực tiếp
        edited_df = st.data_editor(
            st.session_state.df_knowledge,
            column_config={
                "term": st.column_config.TextColumn("Thuật ngữ mới", disabled=True),
                "definition": st.column_config.TextColumn("AI Gợi ý định nghĩa (Sửa tại đây)", width="large"),
                "category": st.column_config.SelectboxColumn("Loại", options=["VÀNG", "TIỀN CÔNG", "HỆ THỐNG"]),
                "is_approved": st.column_config.CheckboxColumn("Nạp?")
            },
            hide_index=True, width='stretch', key="new_term_editor"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 XÁC NHẬN NẠP THÊM", width='stretch', type="primary"):
                to_save = edited_df[edited_df["is_approved"] == True]
                if not to_save.empty:
                    if self.service.approve_and_learn({"terms": to_save.to_dict(orient='records')}):
                        st.success("✅ Đã cập nhật bộ não thành công!")
                        del st.session_state.df_knowledge
                        st.rerun()
        with col2:
            if st.button("🗑️ Hủy kết quả quét", width='stretch'):
                del st.session_state.df_knowledge
                st.rerun()

    def render_approval_interface(self, project_id, project_name="Dự án hiện tại"):
        """Hàm chính điều phối giao diện"""
        st.subheader(f"🧠 Từ điển nghiệp vụ: {project_name}")

        # 1. Lấy dữ liệu từ DB
        with self.service.db.get_session() as session:
            
            existing_knowledge = session.query(VectorKnowledge).all()
            sheets_data = session.query(ExcelSheet).filter_by(project_id=project_id).all()

        known_terms = {k.main_term for k in existing_knowledge if k.definition}

        # 2. Hiển thị tri thức hiện có
        with st.expander("📚 Thư viện tri thức hiện có", expanded=not bool(st.session_state.get('df_knowledge'))):
            if existing_knowledge:
                st.dataframe(pd.DataFrame([{
                    "term": k.main_term, "definition": k.definition, "category": k.category
                } for k in existing_knowledge]), width='stretch', hide_index=True)
            else:
                st.info("Chưa có tri thức nào.")

        st.divider()

        # 3. Nút bấm quét mới
        st.markdown("#### 🔍 Phát hiện thuật ngữ mới")
        if st.button("✨ Quét & Gọi AI định nghĩa mới", type="primary"):
            self._handle_ai_scan(sheets_data, known_terms)

        # 4. Hiển thị bảng duyệt (Nếu có dữ liệu trong session_state)
        self._render_knowledge_editor()

    #-------------------------------------------------------------
    # 2. Xuất và nhâp kiến thức
    #-------------------------------------------------------------
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