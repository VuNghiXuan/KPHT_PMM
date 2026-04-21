import streamlit as st
from config import Config

class KnowledgeView:
    def __init__(self, knowledge_service):
        self.service = knowledge_service

    def render_approval_interface(self, project_id):
        st.subheader("🧠 Quản lý Tri thức Hệ thống")
        st.info("Hệ thống sẽ quét tất cả nhãn từ các Sheet để định nghĩa một lần duy nhất.")

        # Nút quét toàn bộ dự án
        if st.button("🔍 Quét toàn bộ thuật ngữ dự án"):
            with st.spinner("Đang đối soát kho tri thức..."):
                # Gọi hàm xử lý đa sheet mà anh em mình vừa bàn
                report = self.service.process_all_project_labels(project_id)
                st.session_state.current_report = report
        
        # Hiển thị danh sách kết quả quét
        if 'current_report' in st.session_state:
            report = st.session_state.current_report
            
            if not report:
                st.success("Không có thuật ngữ mới cần định nghĩa!")
                return

            with st.form("bulk_approval_form"):
                st.markdown(f"#### Phát hiện {len(report)} thuật ngữ cần xác nhận")
                approved_entries = []
                
                for idx, item in enumerate(report):
                    # Chỉ hiển thị những từ MỚI hoặc GẦN GIỐNG để Vũ duyệt
                    # Những từ đã khớp > 85% sẽ không hiện ở đây cho đỡ rác
                    with st.container():
                        col1, col2 = st.columns([1, 2])
                        
                        # Cột 1: Hiển thị từ gốc và trạng thái
                        with col1:
                            st.markdown(f"**Từ gốc:** `{item['term']}`")
                            if item['status'] == 'SIMILAR':
                                st.caption(f"⚠️ Giống từ: *{item['match_with']}* ({item['score']})")
                            else:
                                st.caption(f"✨ Thuật ngữ mới hoàn toàn")

                        # Cột 2: Ô nhập định nghĩa (Lấy gợi ý từ Service)
                        with col2:
                            # Tự động lấy gợi ý (Config hoặc AI đoán)
                            suggestion = self.service.ai_suggest_definition(item['term'])
                            
                            # Placeholder nhắc Vũ là có thể bỏ trống
                            desc = st.text_input(
                                f"Định nghĩa cho {item['term']}", 
                                value=suggestion,
                                placeholder="Để trống nếu muốn AI tự suy luận sau...",
                                key=f"input_{item['term']}_{idx}"
                            )
                        
                        approved_entries.append({
                            "term": item['term'],
                            "definition": desc,
                            "category": "GLOSSARY"
                        })
                        st.divider()

                # Nút xác nhận lưu
                if st.form_submit_button("✅ Xác nhận & Lưu vào Bộ não AI"):
                    if self.service.approve_and_learn(approved_entries):
                        st.success("Đã nạp tri thức thành công!")
                        # Xóa report sau khi lưu để tránh trùng lặp
                        del st.session_state.current_report
                        st.rerun()

    def render_backup_tools(self, project_id): # Thêm project_id vào đây
        """Công cụ sao lưu tri thức ra file vật lý"""
        st.divider()
        st.subheader("💾 Quản lý file tri thức (JSON)")
        
        col1, col2, col3 = st.columns(3) # Chia làm 3 cột cho đẹp
        
        with col1:
            if st.button("📤 Export Toàn bộ"):
                session = self.service.db.get_session()
                self.service.kv.export_to_json(session, Config.JSON_BACKUP_PATH)
                st.success("Đã backup kho tri thức tổng!")
        
        with col2:
            # --- ĐÂY LÀ NÚT VŨ CẦN ---
            if st.button("🔍 Export Từ Mới (Chưa định nghĩa)"):
                # Gọi hàm xử lý và nhận về chuỗi JSON
                unlabeled_json = self.service.export_unlabeled_to_json(project_id)
                
                if unlabeled_json:
                    st.download_button(
                        label="📥 Tải file JSON từ mới",
                        data=unlabeled_json,
                        file_name=f"unlabeled_project_{project_id}.json",
                        mime="application/json"
                    )
                else:
                    st.info("Không có từ mới nào cần định nghĩa.")

        with col3:
            if st.button("📥 Import Knowledge.json"):
                session = self.service.db.get_session()
                if self.service.kv.import_from_json(session, Config.JSON_BACKUP_PATH):
                    st.success("Đã đồng bộ tri thức!")
                    st.rerun()