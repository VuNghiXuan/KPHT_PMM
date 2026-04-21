import streamlit as st

class Sidebar:
    def __init__(self, db):
        self.db = db

    def render(self):
        st.sidebar.header("🧠 Cấu hình AI")
        brain_list = ["Groq", "Gemini", "Ollama"]
        
        if "brain_provider" not in st.session_state:
            st.session_state.brain_provider = "Gemini"

        choice = st.sidebar.selectbox(
            "Chọn bộ não:", brain_list, 
            index=brain_list.index(st.session_state.brain_provider)
        )
        
        if choice != st.session_state.brain_provider:
            st.session_state.brain_provider = choice
            st.rerun()

        st.sidebar.divider()
        st.sidebar.header("📂 Danh mục Sheets")
        all_sheets = self.db.get_all_sheets()
        
        selected_id = None
        selected_name = None
        selected_pid = None # Khởi tạo biến Project ID
        
        if all_sheets:
            search = st.sidebar.text_input("🔍 Tìm Sheet...", "").lower()
            # Lọc danh sách sheet dựa trên ô tìm kiếm
            filtered = [s for s in all_sheets if search in s.sheet_name.lower()]
            
            if filtered:
                # HIỂN THỊ THÊM TÊN FILE (PROJECT) ĐỂ VŨ KHÔNG CHỌN NHẦM
                # Giả sử Vũ đã join với bảng Project để có thuộc tính project.file_name
                options = {}
                for s in filtered:
                    p_name = getattr(s.project, 'file_name', 'N/A') if hasattr(s, 'project') else "N/A"
                    label = f"{s.sheet_name} (📄 {p_name})"
                    options[label] = s
                
                selected_label = st.sidebar.radio("Chọn Sheet:", list(options.keys()))
                
                # Lấy object sheet tương ứng
                current_sheet = options[selected_label]
                
                selected_id = current_sheet.id
                selected_name = current_sheet.sheet_name
                selected_pid = getattr(current_sheet, 'project_id', None)
        
        # Trả về đủ 3 giá trị cho main.py
        return selected_id, selected_name, selected_pid