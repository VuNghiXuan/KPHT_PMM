# Đường dẫn: ./app_main.py
# Mục đích: File khởi chạy chính của toàn bộ hệ thống Streamlit (Đặt tại thư mục gốc).
# Cấu hình sys.path để Python nhận diện các module bên trong thư mục src/ và UI_tab/.

import sys
import os
import streamlit as st

# Tự động thêm thư mục gốc hiện tại vào sys.path để tránh lỗi ModuleNotFoundError khi import src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import các module giao diện từ thư mục UI_tab
from UI_tab.tab_ingestion import render_ingestion_tab
from UI_tab.tab_extractor import render_extractor_tab
from UI_tab.tab_calculator import render_calculator_tab
from UI_tab.tab_reconciler import render_reconciler_tab
from UI_tab.tab_config_editor import render_config_tab

# --- CẤU HÌNH GIAO DIỆN TRANG WEB ---
st.set_page_config(
    page_title="Hệ Thống Xử Lý Hóa Đơn Vàng & Đối Chiếu Kho",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💎 HỆ THỐNG TỰ ĐỘNG HÓA HÓA ĐƠN & KẾ TOÁN VÀNG BẠC")
st.markdown("---")

# --- TẠO CÁC TAB CHỨC NĂNG ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📁 1. Tiếp nhận File", 
    "🔍 2. Bóc tách OCR", 
    "🧮 3. Tính toán Kho", 
    "📊 4. Đối chiếu Kế toán",
    "⚙️ 5. Cấu hình & Từ điển"
])

# Render nội dung cho từng Tab
with tab1:
    render_ingestion_tab()

with tab2:
    render_extractor_tab()

with tab3:
    render_calculator_tab()

with tab4:
    render_reconciler_tab()

with tab5:
    render_config_tab()