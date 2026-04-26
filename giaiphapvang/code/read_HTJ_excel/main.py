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

# 1. Tắt cảnh báo phiền phức từ các thư viện AI
# warnings.filterwarnings("ignore", category=UserWarning)
# logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
# Chặn các cảnh báo Deprecation từ transformers
warnings.filterwarnings("ignore", category=DeprecationWarning)
# Giảm mức độ log của transformers xuống chỉ hiện lỗi (ERROR) thay vì cảnh báo
logging.getLogger("transformers").setLevel(logging.ERROR)

def main():
    # Cấu hình trang rộng để xem bảng Excel cho sướng mắt
    st.set_page_config(page_title="HTJ Jewelry System", layout="wide", page_icon="💎")
    
    # --- 2. KHỞI TẠO SERVICES (SINGLETON TRONG SESSION STATE) ---
    if 'db' not in st.session_state:
        with st.spinner("🚀 Đang khởi động hệ thống tri thức HTJ..."):
            # Khởi tạo DB Manager
            st.session_state.db = DBManager(Config.DB_URL)
            
            # Khởi tạo Knowledge Manager (VectorDB/Embeddings)
            st.session_state.kv = KnowledgeManager(Config.EMBEDDING_MODEL)
            
            # Khởi tạo Service tổng hợp
            st.session_state.service = KnowledgeService(
                st.session_state.db, 
                st.session_state.kv,
                ai_agent=None  # Vũ có thể gắn Agent vào đây sau
            )

    db = st.session_state.db
    service = st.session_state.service

    # --- 3. SIDEBAR (NƠI ĐIỀU KHIỂN CHÍNH) ---
    sidebar = Sidebar(db)
    # Nhận dữ liệu dưới dạng Dictionary để tránh lỗi thiếu biến (unpacking error)
    sidebar_data = sidebar.render() 

    # --- 4. KHU VỰC TIÊU ĐỀ & IMPORT ---
    st.title("💎 HTJ Jewelry Data Manager")
    
    # Cho phép Vũ upload file bất cứ lúc nào
    with st.expander("📥 Nhập dữ liệu Excel mới"):
        ImportExcelView(db).render()

    # --- 5. ĐIỀU HƯỚNG NỘI DUNG THEO LỰA CHỌN SIDEBAR ---
    if isinstance(sidebar_data, dict) and sidebar_data.get("project_id"):
        pid = sidebar_data["project_id"]
        menu = sidebar_data["menu"]
        sid = sidebar_data["sheet_id"]
        sname = sidebar_data["sheet_name"]

        st.divider()
        st.subheader(f"📂 Đang làm việc: {sidebar_data.get('menu', 'Dashboard')}")

        # --- MENU 1: TỪ ĐIỂN TRI THỨC (QUY HOẠCH VỀ MỘT CHỖ) ---
        if menu == "🧠 Từ điển Tri thức":
            st.info(f"Hệ thống đang quét toàn bộ thuật ngữ của Dự án ID: {pid}")
            k_view = KnowledgeView(service)
            k_view.render_backup_tools(pid)
            
            # TRUYỀN THÊM TÊN DỰ ÁN VÀO ĐÂY (Lấy từ sidebar_data nếu có, hoặc để tạm chuỗi trống)
            p_name = sidebar_data.get("project_name", "Dự án hiện tại")
            k_view.render_approval_interface(pid, p_name)

        # --- MENU 2: QUẢN LÝ KHO / TRANG SỨC / DASHBOARD ---
        # Nếu chọn các menu nghiệp vụ thì mới hiện Tabs dữ liệu
        elif menu in ["🏠 Dashboard", "📦 Quản lý Kho", "💍 Quầy hàng"]:
            if sid:
                tab1, tab2 = st.tabs(["📊 Dữ liệu Sheet", "🤖 AI Procedure"])
                
                with tab1:
                    st.markdown(f"### Bảng dữ liệu: **{sname}**")
                    ExcelView().render_table(db, sid, sname)
                    
                with tab2:
                    AIProcedure(db).render_portal(sid, sname)
            else:
                st.warning("👈 Vui lòng chọn một **Sheet cụ thể** ở Sidebar để xem dữ liệu nghiệp vụ.")

        # --- MENU 3: NGƯỜI DÙNG ---
        elif menu == "👤 Người dùng":
            st.write("Chức năng quản lý nhân viên và phân quyền (Đang phát triển).")

    else:
        # Trạng thái chờ khi chưa có Project nào được chọn
        st.info("👋 Chào anh Vũ! Hãy chọn một **Dự án (File Excel)** ở cột bên trái hoặc **Upload file mới** để bắt đầu.")
        st.image("https://img.freepik.com/free-vector/data-extraction-concept-illustration_114360-4766.jpg", width=400)

if __name__ == "__main__":
    main()