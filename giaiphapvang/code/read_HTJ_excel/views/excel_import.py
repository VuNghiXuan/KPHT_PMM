import streamlit as st
import os
from core.excel_miner import ExcelMiner
from config import Config

class ImportExcelView:
    def __init__(self, db_manager):
        self.db = db_manager

    def render(self):
        with st.expander("📥 Nhập File Excel Gốc"):
            uploaded_file = st.file_uploader("Kéo thả file .xlsx", type=["xlsx"])
            if uploaded_file and st.button("🚀 Xử lý & Lưu Database"):
                temp_path = os.path.join(Config.RAW_EXCEL_DIR, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                with st.spinner("Đang phân tích cấu trúc file ..."):
                    miner = ExcelMiner(temp_path)
                    objs = miner.scan_project()
                    miner.close()
                    
                    # SỬA DÒNG NÀY: Truyền thêm tên file làm tên Project
                    self.db.save_project_data(uploaded_file.name, objs) 
                    
                    st.cache_data.clear()
                    st.success(f"Đã nạp dự án '{uploaded_file.name}' thành công!")
                    st.rerun()