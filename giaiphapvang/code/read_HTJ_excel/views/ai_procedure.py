import streamlit as st
from core.ai_manager import AIManager
import io

class AIProcedure:
    def __init__(self, db):
        self.db = db
        self.current_brain = st.session_state.get("brain_provider", "Gemini")
        self.ai = AIManager(provider=self.current_brain)

    def render_portal(self, sheet_id, sheet_name):
        st.subheader(f"📝 Quản lý Quy trình: {sheet_name}")
        st.info(f"🤖 Bộ não AI đang trực chiến: **{self.current_brain}**")

        # 1. Lấy dữ liệu Excel gốc
        clean_text = self.db.get_sheet_data_as_cleaned_text(sheet_id)
        
        # 2. Quản lý nội dung hiển thị qua Session State để AI cập nhật là thấy ngay
        old_kb = self.db.get_knowledge_by_sheet(sheet_id)
        db_content = old_kb.content if old_kb else ""

        # Khởi tạo hoặc cập nhật nội dung vào bộ nhớ tạm của Streamlit
        if f"content_{sheet_id}" not in st.session_state:
            st.session_state[f"content_{sheet_id}"] = db_content

        # 3. Giao diện hiển thị
        st.markdown("### ✍️ Nội dung quy trình hệ thống")
        
        # Nút chuyển đổi chế độ Chỉnh sửa
        is_edit = st.toggle("🔓 Chế độ chỉnh sửa nội dung", value=False)

        if is_edit:
            # Chế độ Chỉnh sửa
            user_draft = st.text_area(
                "Nội dung soạn thảo:",
                value=st.session_state[f"content_{sheet_id}"],
                height=500,
                key=f"input_{sheet_id}"
            )
            # Cập nhật lại session state khi user gõ
            st.session_state[f"content_{sheet_id}"] = user_draft
        else:
            # Chế độ Chỉ xem (Dùng Markdown để hiển thị đẹp hơn)
            if st.session_state[f"content_{sheet_id}"]:
                st.markdown(f'<div style="border:1px solid #ccc; padding:15px; border-radius:5px; background-color:#f9f9f9; color:black">{st.session_state[f"content_{sheet_id}"]}</div>', unsafe_allow_html=True)
            else:
                st.warning("Chưa có nội dung quy trình.")

        # 4. Cụm nút điều khiển
        st.write("---")
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if is_edit:
                if st.button("💾 Lưu vào DB", use_container_width=True):
                    content_to_save = st.session_state[f"content_{sheet_id}"]
                    if content_to_save:
                        self.db.save_knowledge(sheet_id, "Quy trình vận hành", content_to_save, "Manual Edit")
                        st.success("Đã lưu!")
                        st.rerun()

        with col2:
            btn_label = f"🪄 {self.current_brain} Biên soạn"
            if st.button(btn_label, type="primary", use_container_width=True):
                with st.spinner(f"AI {self.current_brain} đang làm việc..."):
                    instruction = f"Cấu trúc Excel: {clean_text}\nNội dung hiện tại: {st.session_state[f'content_{sheet_id}']}"
                    result = self.ai.generate_htj_procedure(sheet_name, instruction)
                    
                    if result:
                        # Cập nhật session state ngay lập tức để hiển thị lên màn hình
                        st.session_state[f"content_{sheet_id}"] = result
                        # Lưu vào DB luôn
                        self.db.save_knowledge(sheet_id, "Quy trình vận hành", result, self.current_brain)
                        st.success("AI đã soạn xong!")
                        st.rerun()

        # 5. Xuất file đa định dạng
        if st.session_state[f"content_{sheet_id}"]:
            st.write("📥 **Xuất bản tài liệu:**")
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            current_content = st.session_state[f"content_{sheet_id}"]
            file_name = f"HTJ_QuyTrinh_{sheet_name}"

            with exp_col1:
                st.download_button("Tải .TXT", current_content, f"{file_name}.txt")
            
            with exp_col2:
                # Xuất file .DOC (Dạng thô đơn giản cho Word đọc được)
                doc_content = current_content.replace('\n', '\r\n')
                st.download_button("Tải .DOC", doc_content, f"{file_name}.doc")

            with exp_col3:
                # Xuất file PDF (Dùng thư viện chuyển đổi đơn giản hoặc hướng dẫn Vũ cài thêm)
                # Tạm thời xuất Markdown để in ra PDF chuẩn nhất
                st.download_button("Tải .PDF (Markdown)", current_content, f"{file_name}.md", help="Mở file này bằng trình duyệt hoặc Word rồi Print to PDF là đẹp nhất.")

        st.divider()
        with st.expander("👁️ Xem Context Excel"):
            st.text_area("Context:", clean_text, height=100)