import streamlit as st
from database.db_manager import DBManager
from database.knowledge_service import KnowledgeService
from database.knowledge_manager import KnowledgeManager
from views.excel_import import ImportExcelView
from views.knowledge_manager import KnowledgeView
from views.render_excel import ExcelView
from views.siderbar import Sidebar
from views.ai_procedure import AIProcedure
from config import Config


import warnings
import logging

# Tắt cảnh báo từ thư viện
warnings.filterwarnings("ignore", category=UserWarning)
# Tắt log từ logging của transformers
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)

def main():
    st.set_page_config(page_title="HTJ Jewelry System", layout="wide")
    
    # --- KHỞI TẠO SERVICES (CHỈ CHẠY 1 LẦN) ---
    if 'service' not in st.session_state:
        with st.spinner("🚀 Đang khởi động bộ não AI HTJ..."):
            st.session_state.db = DBManager(Config.DB_URL)
            st.session_state.kv = KnowledgeManager(Config.EMBEDDING_MODEL)
            
            # GIẢ SỬ Vũ có 1 biến agent ở đây (có thể lấy từ config hoặc session)
            # agent = SmartJewelryAgent() 
            
            st.session_state.service = KnowledgeService(
                st.session_state.db, 
                st.session_state.kv,
                ai_agent=None # <--- Tạm thời để None nếu Vũ chưa muốn dùng AI gợi ý
            )

    db = st.session_state.db
    service = st.session_state.service

    # 1. Sidebar - sidebar.render() nên trả về thêm pid (Project ID)
    sidebar = Sidebar(db)
    # Giả sử hàm render của Vũ trả về: sid (sheet_id), sname (sheet_name), pid (project_id)
    # Nếu Sidebar chưa trả về pid, Vũ hãy cập nhật Sidebar để lấy pid = sheet.project_id
    sid, sname, pid = sidebar.render() 

    st.title("💎 HTJ Jewelry Data Manager")
    
    # 2. View Nhập File Excel
    ImportExcelView(db).render()

    # 3. Khu vực hiển thị nội dung chính
    if sid:
        st.divider()
        tab1, tab2, tab3 = st.tabs(["📊 Bảng Dữ Liệu", "🧠 Định nghĩa tri thức", "🤖 AI Procedure"])
        
        with tab1:
            ExcelView().render_table(db, sid, sname)
            
        with tab2:
            k_view = KnowledgeView(service)
            # THAY ĐỔI: Truyền pid thay vì sid để quét tri thức toàn dự án
            # Giúp Vũ không phải định nghĩa lặp đi lặp lại ở từng sheet
            k_view.render_approval_interface(pid) 
            k_view.render_backup_tools(pid)
            
        with tab3:
            AIProcedure(db).render_portal(sid, sname)
    else:
        st.info("👈 Vui lòng chọn Sheet bên trái để bắt đầu làm việc.")

if __name__ == "__main__":
    main()