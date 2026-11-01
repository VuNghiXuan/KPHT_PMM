# ==============================================================================
# Đường dẫn: Couting_support/UI_tab/tab_config_editor.py
# Mục đích: Module giao diện Tab 5 (Streamlit) - Quản lý cấu hình cấu trúc cột và 
#           từ điển từ đồng nghĩa theo giao diện trực quan, liền mạch, dễ thao tác.
# Hàm chính: render_config_tab()
# ==============================================================================

import os
import json
import streamlit as st

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")

def load_config():
    """Hàm tải cấu hình từ file config.json."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"target_columns": [], "column_synonyms": {}}

def save_config(config_data):
    """Hàm ghi lưu cấu hình mới vào file config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def render_config_tab():
    """
    Hàm chính render giao diện Tab 5 tối ưu hóa trải nghiệm thao tác:
    - Hiển thị danh sách cột và từ đồng nghĩa song song trên cùng một màn hình.
    - Sửa trực tiếp từ khóa, dịch chuyển thứ tự cột (lên/xuống), xóa hoặc thêm nhanh ở cuối bảng.
    """
    st.header("⚙️ 5. Quản lý Cấu hình & Từ điển Từ đồng nghĩa")
    st.write("Tùy chỉnh trực tiếp tên cột, thứ tự hiển thị và từ khóa nhận diện OCR ngay bên dưới mỗi mục.")
    
    if not os.path.exists(CONFIG_PATH):
        st.error("⚠️ Không tìm thấy file `config.json` tại thư mục gốc!")
        return

    config = load_config()
    target_columns = config.get("target_columns", [])
    synonyms = config.get("column_synonyms", {})

    st.markdown("---")

    # --- KHU VỰC HIỂN THỊ & CHỈNH SỬA DANH SÁCH CỘT HIỆN TẠI ---
    updated_columns = []
    updated_synonyms = {}
    
    # Dùng form hoặc container gọn gàng để quản lý danh sách
    for idx, col_name in enumerate(target_columns):
        # Bố trí các thành phần trên cùng một hàng ngang trực quan: [STT] [Tên cột & Từ đồng nghĩa] [Nút dịch chuyển] [Nút xóa]
        with st.container():
            col_idx, col_main, col_actions = st.columns([0.6, 7.4, 2.0])
            
            with col_idx:
                st.markdown(f"**#{idx + 1}**")
                
            with col_main:
                # Cho phép sửa trực tiếp tên cột
                new_col_name = st.text_input(f"Tên cột {idx+1}", value=col_name, key=f"col_name_{idx}", label_visibility="collapsed")
                
                # Lấy danh sách từ đồng nghĩa hiện tại
                current_syns = synonyms.get(col_name, [col_name])
                syn_val = st.text_input(
                    f"Từ đồng nghĩa của {col_name}", 
                    value=", ".join(current_syns), 
                    key=f"syn_{idx}", 
                    placeholder="Nhập từ khóa, cách nhau bằng dấu phẩy...",
                    label_visibility="collapsed"
                )
                
                # Lưu tạm vào danh sách cập nhật
                final_col_name = new_col_name.strip() if new_col_name.strip() else col_name
                updated_columns.append(final_col_name)
                updated_synonyms[final_col_name] = [k.strip() for k in syn_val.split(",") if k.strip()]

            with col_actions:
                # Cụm nút thao tác nhanh nằm ngay cạnh dòng dữ liệu
                c_up, c_down, c_del = st.columns(3)
                with c_up:
                    if idx > 0 and st.button("⬆️", key=f"up_{idx}", help="Di chuyển lên"):
                        target_columns[idx], target_columns[idx - 1] = target_columns[idx - 1], target_columns[idx]
                        config["target_columns"] = target_columns
                        save_config(config)
                        st.rerun()
                with c_down:
                    if idx < len(target_columns) - 1 and st.button("⬇️", key=f"down_{idx}", help="Di chuyển xuống"):
                        target_columns[idx], target_columns[idx + 1] = target_columns[idx + 1], target_columns[idx]
                        config["target_columns"] = target_columns
                        save_config(config)
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"del_{idx}", help="Xóa cột này"):
                        target_columns.pop(idx)
                        if col_name in synonyms:
                            del synonyms[col_name]
                        config["target_columns"] = target_columns
                        config["column_synonyms"] = synonyms
                        save_config(config)
                        st.rerun()
            
            st.markdown("<hr style='margin: 5px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)

    # --- KHU VỰC THÊM CỘT MỚI Ở CUỐI DANH SÁCH ---
    st.markdown("### ➕ Thêm cột mục tiêu mới")
    with st.form("form_add_column", clear_on_submit=True):
        col_new_1, col_new_2 = st.columns([4, 6])
        with col_new_1:
            added_col_name = st.text_input("Tên cột mới", placeholder="Ví dụ: Ghi chú kho")
        with col_new_2:
            added_col_syns = st.text_input("Từ đồng nghĩa (phân cách dấu phẩy)", placeholder="Ví dụ: Ghi chú, Note, Chú thích")
            
        submitted_add = st.form_submit_button("➕ Thêm vào cuối danh sách")
        if submitted_add:
            if added_col_name.strip():
                clean_name = added_col_name.strip()
                if clean_name in target_columns:
                    st.warning("⚠️ Tên cột này đã tồn tại trong hệ thống!")
                else:
                    target_columns.append(clean_name)
                    updated_synonyms[clean_name] = [k.strip() for k in added_col_syns.split(",") if k.strip()] or [clean_name]
                    config["target_columns"] = target_columns
                    config["column_synonyms"] = updated_synonyms
                    save_config(config)
                    st.success(f"✅ Đã thêm cột '{clean_name}' thành công!")
                    st.rerun()
            else:
                st.warning("⚠️ Vui lòng nhập tên cột mới hợp lệ.")

    # --- NÚT LƯU TỔNG THỂ ---
    st.markdown("---")
    col_save_btn, _ = st.columns([3, 7])
    with col_save_btn:
        if st.button("💾 Lưu toàn bộ cấu hình hệ thống", type="primary", use_container_width=True):
            config["target_columns"] = updated_columns
            config["column_synonyms"] = updated_synonyms
            save_config(config)
            st.success("🎉 Đã cập nhật file `config.json` thành công!")