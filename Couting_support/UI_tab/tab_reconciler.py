# ==============================================================================
# Đường dẫn: Couting_support/UI_tab/tab_reconciler.py
# Mục đích: Giao diện Tab 4 (Streamlit) - Đối chiếu chéo hoàn toàn độc lập,
#           cung cấp 2 khung upload file riêng biệt (File Nội Bộ & File Đối Tác),
#           bóc tách đa sheet, chạy thuật toán so khớp dòng (Cosine / SequenceMatcher),
#           hiển thị tỷ lệ khớp % và tích hợp nút xuất file Excel báo cáo.
# Hàm chính: render_reconciler_tab()
# ==============================================================================

import os
import time
import streamlit as st
import pandas as pd
from src.extractor import InvoiceExtractor
from src.reconciler import InvoiceReconciler

def render_reconciler_tab():
    """
    Hàm chính render giao diện Tab 4: Đối chiếu chéo độc lập, không phụ thuộc Tab 2.
    Cho phép upload trực tiếp cả file nội bộ và file đối tác ngay trên màn hình.
    """
    st.header("📊 4. Đối chiếu Chéo Dữ liệu & Xuất Báo cáo Excel")
    st.write("Tab hoạt động độc lập: Tải lên trực tiếp cả **File Nội Bộ** và **File Đối Tác** ở bên dưới, hệ thống sẽ tự động bóc tách đa sheet và chạy thuật toán so khớp tỷ lệ dòng.")

    st.markdown("---")
    
    # Chia 2 cột để upload 2 file độc lập ngay tại Tab 4
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        st.markdown("### 📂 1. File Dữ liệu Nội Bộ")
        has_tab2_data = "df_extracted" in st.session_state and st.session_state["df_extracted"] is not None and not st.session_state["df_extracted"].empty
        
        use_tab2 = False
        if has_tab2_data:
            use_tab2 = st.checkbox("Sử dụng dữ liệu từ Tab 2", value=True)

        internal_file = None
        if not use_tab2:
            internal_file = st.file_uploader("Tải lên file nội bộ (Excel/CSV)", type=["xlsx", "xls", "csv"], key="internal_file_upload_tab4")
        else:
            st.info(f"Đang dùng dữ liệu sẵn có từ Tab 2 ({len(st.session_state['df_extracted'])} dòng).")

    with col_up2:
        st.markdown("### 📂 2. File Dữ liệu Đối Tác / Kế Toán")
        external_file = st.file_uploader("Tải lên file đối tác (Excel/CSV)", type=["xlsx", "xls", "csv"], key="external_file_upload_tab4")

    # Xử lý lấy DataFrame nội bộ
    system_df = None
    if use_tab2 and has_tab2_data:
        system_df = st.session_state["df_extracted"]
    elif internal_file is not None:
        temp_dir = "input_files"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        safe_int_name = f"internal_upload_{int(time.time())}_{internal_file.name}"
        int_path = os.path.join(temp_dir, safe_int_name)
        with open(int_path, "wb") as f:
            f.write(internal_file.getbuffer())
        
        # Bóc tách file nội bộ độc lập
        temp_rec_helper = InvoiceReconciler(pd.DataFrame())
        with st.spinner("Đang bóc tách file dữ liệu nội bộ..."):
            system_df, int_msg = temp_rec_helper.load_external_file_multisheet(int_path)
            if system_df is not None:
                st.success(f"✅ Đã tải file nội bộ: {len(system_df)} dòng.")
            else:
                st.error(f"❌ Lỗi đọc file nội bộ: {int_msg}")

    # Khi đã có đủ 2 nguồn dữ liệu, hiển thị khu vực xử lý đối chiếu
    if system_df is not None and not system_df.empty and external_file is not None:
        temp_dir = "input_files"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        safe_ext_name = f"external_upload_{int(time.time())}_{external_file.name}"
        ext_path = os.path.join(temp_dir, safe_ext_name)
        with open(ext_path, "wb") as f:
            f.write(external_file.getbuffer())

        reconciler = InvoiceReconciler(system_df)

        with st.spinner("Đang bóc tách đa sheet file đối tác..."):
            external_df, ext_msg = reconciler.load_external_file_multisheet(ext_path)

        if external_df is not None:
            st.success(f"✅ Đã đọc thành công {len(external_df)} dòng từ file đối tác!")
            
            with st.expander("👁️ Xem trước dữ liệu 2 bên trước khi đối chiếu"):
                st.markdown("**Dữ liệu Nội bộ:**")
                st.dataframe(system_df.head(3), width='stretch')
                st.markdown("**Dữ liệu Đối tác:**")
                st.dataframe(external_df.head(3), width='stretch')

            st.markdown("---")
            if st.button("🚀 Bắt đầu Chạy Đối Chiếu Chéo (Cosine & SequenceMatcher)", type="primary", key="btn_run_independent_reconcile"):
                with st.spinner("Đang tính toán tỷ lệ tương đồng dòng giữa 2 file..."):
                    report_df, rep_msg = reconciler.compare_datasets_with_cosine(external_df)

                if report_df is not None:
                    st.success("🎉 Hoàn tất quá trình đối chiếu chéo thành công!")
                    st.session_state["df_reconcile_report"] = report_df

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        matched = len(report_df[report_df['Trạng thái'] == 'Khớp'])
                        st.metric("✅ Khớp dữ liệu", matched)
                    with c2:
                        diff = len(report_df[report_df['Trạng thái'] == 'Lệch dữ liệu'])
                        st.metric("⚠️ Lệch dữ liệu", diff)
                    with c3:
                        missing = len(report_df[report_df['Trạng thái'] == 'Chỉ có ở Đối tác'])
                        st.metric("📌 Chỉ có ở Đối tác", missing)

                    st.markdown("### 📋 Bảng Báo cáo Vết Chi Tiết (Sheet, Dòng & Tỷ lệ Khớp)")
                    st.dataframe(report_df, width='stretch')

                    st.markdown("---")
                    st.subheader("📥 Xuất Báo Cáo Ra File Excel")
                    if st.button("💾 Tải xuống Báo cáo Đối chiếu (.xlsx)", key="btn_export_excel_report_ind"):
                        excel_path, exp_msg = reconciler.export_report_to_excel(report_df)
                        if excel_path:
                            st.success(f"✅ {exp_msg} Lưu tại: `{excel_path}`")
                            with open(excel_path, "rb") as f:
                                st.download_button(
                                    label="📥 Bấm vào đây để tải file Excel",
                                    data=f,
                                    file_name="Bao_Cao_Doi_Chieu_Kho.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.error(f"❌ {exp_msg}")
                else:
                    st.error(f"❌ Lỗi đối chiếu: {rep_msg}")
        else:
            st.error(f"❌ Lỗi đọc file đối tác: {ext_msg}")
    else:
        st.info("💡 **Hướng dẫn:** Vui lòng chọn hoặc tải lên đầy đủ cả **File Nội Bộ** (hoặc tích chọn dùng dữ liệu Tab 2) và **File Đối Tác** ở trên để kích hoạt nút đối chiếu độc lập.")