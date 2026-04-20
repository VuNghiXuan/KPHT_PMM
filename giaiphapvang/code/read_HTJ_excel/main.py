import streamlit as st
import pandas as pd
import os
import json
from core.excel_miner import ExcelMiner
from database.db_manager import DBManager
from core.ai_manager import AIManager 

# --- HÀM HỖ TRỢ XỬ LÝ DATAFRAME ---
def build_df(rows_data, headers):
    """Chuyển đổi dữ liệu từ DB thành DataFrame để hiển thị bảng"""
    if not rows_data: 
        return pd.DataFrame()
    
    # Trích xuất giá trị từ cấu trúc cell {"value": "...", "color": "..."}
    matrix = []
    for r in rows_data:
        row_values = [cell.get('value', '') for cell in r.get('cells', [])]
        matrix.append(row_values)
        
    indices = [r.get('row_index') for r in rows_data]
    df = pd.DataFrame(matrix, columns=headers, index=indices)
    return df

def render_view():
    st.set_page_config(page_title="HTJ Jewelry System", layout="wide")
    
    # Khởi tạo Database Manager
    db = DBManager()

    # --- 1. SIDEBAR: CẤU HÌNH AI ---
    st.sidebar.header("🧠 Cấu hình AI")
    
    if "brain_provider" not in st.session_state:
        st.session_state.brain_provider = "Gemini"

    brain_list = ["Gemini", "Groq", "Ollama"]
    brain_choice = st.sidebar.selectbox(
        "Chọn bộ não soạn quy trình:",
        brain_list,
        index=brain_list.index(st.session_state.brain_provider),
        key="brain_selector_main"
    )
    
    # Cập nhật bộ não nếu có thay đổi
    if brain_choice != st.session_state.brain_provider:
        st.session_state.brain_provider = brain_choice
        st.rerun()

    ai_brain = AIManager(provider=st.session_state.brain_provider)

    st.sidebar.divider()

    # --- 2. SIDEBAR: DANH MỤC SHEETS ---
    st.sidebar.header("📂 Danh mục Sheets")
    all_sheets = db.get_all_sheets()
    selected_sheet_id = None
    choice = None
    
    if all_sheets:
        search_sheet = st.sidebar.text_input("🔍 Tìm tên Sheet...", "").lower()
        # Lọc danh sách sheet theo từ khóa tìm kiếm
        filtered_sheets = [s for s in all_sheets if search_sheet in s.sheet_name.lower()]
        
        if filtered_sheets:
            sheet_names = [s.sheet_name for s in filtered_sheets]
            # Radio button để chọn sheet
            choice = st.sidebar.radio("Chọn Sheet để xem dữ liệu:", sheet_names)
            
            # Lấy ID của sheet đang chọn
            for s in filtered_sheets:
                if s.sheet_name == choice:
                    selected_sheet_id = s.id
                    break

    # --- 3. MAIN UI ---
    st.title("💎 HTJ Jewelry Data Manager")
    
    with st.expander("📥 Nhập File Excel Gốc (Upload mới)"):
        uploaded_file = st.file_uploader("Kéo thả file vào đây", type=["xlsx"])
        if uploaded_file and st.button("🚀 Xử lý & Lưu Database"):
            os.makedirs("storage/raw_excel", exist_ok=True)
            temp_path = f"storage/raw_excel/{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("Đang phân tích cấu trúc vàng..."):
                miner = ExcelMiner(temp_path)
                objs = miner.scan_project()
                miner.close()
                db.save_project_data(objs)
                st.cache_data.clear() # Xóa cache để đảm bảo dữ liệu mới hiện lên
                st.success("Đã đồng bộ thành công! Vui lòng chọn Sheet ở Sidebar.")
                st.rerun()

    # --- 4. KHU VỰC HIỂN THỊ DỮ LIỆU ---
    if selected_sheet_id:
        st.divider()
        # Tạo 2 Tab: Bảng dữ liệu và AI
        tab_table, tab_ai = st.tabs(["📊 Bảng Dữ Liệu Excel", "🤖 AI Agent Portal"])

        with tab_table:
            # Lấy dữ liệu trực tiếp (bỏ cache đoạn này để tránh lỗi không hiện bảng)
            rows_data, headers = db.get_data_by_sheet_as_table(selected_sheet_id)
            
            if rows_data:
                st.subheader(f"Dữ liệu bảng: {choice}")
                
                # Xây dựng DataFrame
                df_full = build_df(rows_data, headers)
                
                # Thanh tìm kiếm nội dung trong bảng
                search_data = st.text_input("🔍 Tìm kiếm nhanh trong bảng...", key="table_search")
                
                if search_data:
                    mask = df_full.apply(lambda row: row.astype(str).str.contains(search_data, case=False).any(), axis=1)
                    df_display = df_full[mask]
                else:
                    df_display = df_full
                
                # Hiển thị bảng lên giao diện (Đây là phần Vũ cần nhất)
                st.dataframe(
                    df_display, 
                    use_container_width=True, 
                    height=600,
                    column_config={"row_index": st.column_config.NumberColumn("Dòng")}
                )
            else:
                st.warning("Sheet này không có dữ liệu hoặc lỗi cấu trúc.")

        with tab_ai:
            st.subheader("📝 Biên soạn quy trình tự động")
            st.info(f"🧠 Bộ não đang sẵn sàng: **{st.session_state.brain_provider}**")
            
            # Lấy dữ liệu nén
            clean_text = db.get_sheet_data_as_cleaned_text(selected_sheet_id)
            
            if clean_text and "Không có dữ liệu" not in clean_text:
                if st.button(f"🚀 Ra lệnh cho {st.session_state.brain_provider} soạn quy trình"):
                    with st.spinner("AI đang làm việc..."):
                        result = ai_brain.generate_htj_procedure(choice, clean_text)
                        st.markdown("---")
                        st.markdown(result)
                        st.download_button("📥 Tải bản thảo (.md)", result, file_name=f"HTJ_{choice}.md")
                
                with st.expander("👁️ Xem dữ liệu nén đã gửi cho AI"):
                    st.text_area("Nội dung gửi:", clean_text, height=200)
            else:
                st.error("Dữ liệu không đủ để AI xử lý. Hãy kiểm tra lại file Excel.")

    else:
        # Nếu chưa chọn sheet nào
        st.info("👈 Vui lòng chọn một Sheet từ danh sách bên trái để bắt đầu.")

if __name__ == "__main__":
    render_view()