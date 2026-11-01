# Đường dẫn: ./UI_tab/tab_ingestion.py
# Mục đích: Giao diện Tab 1 - Tiếp nhận, tải lên và quản lý file hóa đơn đầu vào.

import os
import streamlit as st
import pandas as pd

def render_ingestion_tab():
    """Hàm render giao diện Quản lý & Tiếp nhận file đầu vào."""
    st.header("📁 1. Tiếp nhận và Quản lý File Đầu Vào")
    st.write("Tải lên hóa đơn (PDF, Ảnh JPG/PNG, XML, Excel) vào hệ thống.")
    
    uploaded_files = st.file_uploader(
        "Chọn file hóa đơn:",
        type=["pdf", "jpg", "jpeg", "png", "xml", "xlsx"],
        accept_multiple_files=True
    )
    
    input_dir = "input_files"
    os.makedirs(input_dir, exist_ok=True)
    
    if uploaded_files:
        if st.button("💾 Lưu file vào hệ thống"):
            for file in uploaded_files:
                with open(os.path.join(input_dir, file.name), "wb") as f:
                    f.write(file.getbuffer())
            st.success("Đã lưu trữ file thành công!")
            
    st.markdown("### 📂 Danh sách file trong thư mục `input_files/`")
    if os.path.exists(input_dir):
        files = os.listdir(input_dir)
        if files:
            st.dataframe(pd.DataFrame({"Tên file": files}), width='stretch')
        else:
            st.info("Thư mục trống.")