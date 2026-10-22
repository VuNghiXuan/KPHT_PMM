# Đường dẫn: ./UI_tab/tab_calculator.py
# Mục đích: Giao diện Tab 3 - Tính toán kho và áp dụng quy tắc suy luận nghiệp vụ.

import sys
import os
import streamlit as st

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.calculator import process_calculation

def render_calculator_tab():
    """Hàm render giao diện Tính toán Kho & Suy luận nghiệp vụ."""
    st.header("🧮 3. Tính toán & Suy luận Nghiệp vụ Kho")
    st.write("Áp dụng công thức tính trọng lượng vàng và tổng giá thành tự động.")
    
    if "df_extracted" in st.session_state:
        st.dataframe(st.session_state["df_extracted"], width='stretch')
        if st.button("⚙️ Chạy tính toán kho"):
            df_proc = process_calculation(st.session_state["df_extracted"])
            st.success("Hoàn tất tính toán!")
            st.dataframe(df_proc, width='stretch')
            st.session_state["df_processed"] = df_proc
    else:
        st.warning("Vui lòng chạy bóc tách ở Tab 2 trước.")