import streamlit as st

class Sidebar:
    def __init__(self, db):
        self.db = db

    def render(self):
        # 1. CẤU HÌNH AI (Giữ nguyên phần chọn bộ não)
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

        # 2. CHỌN FILE EXCEL (PROJECT) - TRÍCH XUẤT TỪ DB
        st.sidebar.header("📁 Chọn Dự án (File Excel)")
        all_projects = self.db.get_all_projects() # Hàm lấy danh sách project từ DB
        
        if not all_projects:
            st.sidebar.warning("Chưa có file Excel nào trong hệ thống.")
            return {"project_id": None, "menu": None, "sheet_id": None, "sheet_name": None}

        # Tạo danh sách hiển thị và mặc định chọn file cuối cùng
        project_options = {p.file_name: p for p in all_projects}
        project_names = list(project_options.keys())
        
        selected_p_name = st.sidebar.selectbox(
            "Chọn file gốc:", 
            options=project_names,
            index=len(project_names) - 1 # Mặc định file cuối cùng
        )
        
        current_project = project_options[selected_p_name]
        selected_pid = current_project.id

        st.sidebar.divider()

        # 3. HIỂN THỊ MENU CHỨC NĂNG (Sau khi đã chọn File)
        # Sử dụng radio hoặc selectbox để làm menu chính
        menu_choice = st.sidebar.radio(
            "📍 Menu Chức năng",
            ["🏠 Dashboard", "🧠 Từ điển Tri thức", "👤 Người dùng"]
        )

        st.sidebar.divider()

        # 4. DANH MỤC SHEETS (Chỉ lọc theo Project đã chọn)
        st.sidebar.header("📄 Danh sách Sheets")
        # Lấy các sheet thuộc project_id đang chọn từ DB
        sheets_in_project = self.db.get_sheets_by_project(selected_pid) 
        
        selected_id = None
        selected_name = None

        if sheets_in_project:
            # Ô tìm kiếm sheet nội bộ trong file
            search = st.sidebar.text_input("🔍 Tìm nhanh Sheet...", "").lower()
            filtered = [s for s in sheets_in_project if search in s.sheet_name.lower()]
            
            if filtered:
                sheet_labels = {s.sheet_name: s for s in filtered}
                selected_s_name = st.sidebar.radio("Chọn Sheet để xem chi tiết:", list(sheet_labels.keys()))
                
                current_sheet = sheet_labels[selected_s_name]
                selected_id = current_sheet.id
                selected_name = current_sheet.sheet_name
            else:
                st.sidebar.info("Không tìm thấy sheet phù hợp.")
        
        # Trả về các thông tin quan trọng để Main.py điều hướng
        return {
            "project_id": selected_pid,
            "menu": menu_choice,
            "sheet_id": selected_id,
            "sheet_name": selected_name
        }
    