# ==============================================================================
# Đường dẫn: Couting_support/UI_tab/tab_extractor.py
# Mục đích: Module giao diện Tab 2 trên Streamlit. Quản lý quy trình hiển thị
#           kiểm tra nội dung thô và chạy tiến trình bóc tách 18 cột chính thức.
# Hàm chính: render_extractor_tab()
# ==============================================================================

import sys
import os
import streamlit as st

# Tự động đồng bộ sys.path để đảm bảo luôn import được module từ src/
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.extractor import InvoiceExtractor, extract_invoice_data

def render_extractor_tab():
    """
    Hàm chính khởi tạo và render toàn bộ giao diện của Tab 2.
    Bao gồm 2 sub-tab: Xem dữ liệu thô & Bóc tách chuẩn hóa 18 cột.
    """
    st.header("🔍 2. Đọc & Bóc tách Dữ liệu Chứng từ")
    st.write("Quét và phân tích các chứng từ trong thư mục `input_files/` (Đọc từng Sheet Excel, Ảnh, PDF, XML).")
    
    input_folder = "input_files"
    
    tab_raw, tab_table = st.tabs(["📄 Xem nội dung thô (Kiểm tra multi-sheet)", "📊 Bóc tách chuẩn 18 cột (Chính thức)"])
    
    # --- TAB CON 1: XEM NỘI DUNG THÔ ---
    with tab_raw:
        st.markdown("### 👁️ Kiểm tra nội dung văn bản & Dữ liệu gốc từ chứng từ")
        if st.button("🔎 Quét nội dung thô các file", key="btn_scan_raw"):
            if not os.path.exists(input_folder) or not os.listdir(input_folder):
                st.warning("⚠️ Thư mục `input_files/` đang trống. Vui lòng tải file ở Tab 1.")
            else:
                extractor = InvoiceExtractor()
                for file_name in os.listdir(input_folder):
                    if file_name.startswith("~$"):
                        continue
                        
                    file_path = os.path.join(input_folder, file_name)
                    if not os.path.isfile(file_path):
                        continue
                        
                    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
                    
                    with st.expander(f"📄 File: `{file_name}` ({ext.upper()})", expanded=True):
                        if ext in ['xlsx', 'xls']:
                            rows = extractor.extract_rows_from_excel_multisheet(file_path)
                            if rows:
                                st.write(f"✅ Đã quét từng sheet và trích xuất thành công {len(rows)} dòng dữ liệu:")
                                st.dataframe(rows, width='stretch')
                            else:
                                st.info("File Excel trống hoặc không khớp từ điển cột.")
                        else:
                            lines = []
                            if ext in ['jpg', 'jpeg', 'png']:
                                lines = extractor.extract_text_from_image(file_path)
                            elif ext == 'pdf':
                                lines = extractor.extract_text_from_pdf(file_path)
                            elif ext == 'xml':
                                lines = extractor.parse_xml(file_path)
                                
                            if lines:
                                st.text_area(f"Nội dung thô - {file_name}", value="\n".join(lines), height=150, key=f"raw_{file_name}")
                            else:
                                st.info("Không đọc được văn bản hoặc file trống.")

    # --- TAB CON 2: BÓC TÁCH CHUẨN HÓA 18 CỘT ---
    with tab_table:
        st.markdown("### 📊 Trích xuất dữ liệu tự động sang 18 cột mục tiêu")
        if st.button("🚀 Bắt đầu bóc tách & Chuẩn hóa 18 cột", key="btn_run_structured"):
            try:
                with st.spinner("Đang duyệt các sheet Excel và phân tích dữ liệu... Vui lòng đợi."):
                    df_result = extract_invoice_data(input_folder=input_folder)
                    
                if df_result is not None and not df_result.empty:
                    st.success(f"✅ Đã chuẩn hóa thành công {len(df_result)} dòng chứng từ từ tất cả các file/sheet!")
                    st.dataframe(df_result, width='stretch')
                    # Lưu trữ dữ liệu vào session_state cho Tab 3 (Calculator)
                    st.session_state["df_extracted"] = df_result
                else:
                    st.warning("⚠️ Không tìm thấy dữ liệu hợp lệ để bóc tách.")
            except Exception as e:
                st.error(f"❌ Lỗi trong quá trình bóc tách: {e}")