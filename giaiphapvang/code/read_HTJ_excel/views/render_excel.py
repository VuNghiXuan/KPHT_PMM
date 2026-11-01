import streamlit as st
import pandas as pd


class ExcelView:
    @staticmethod
    def build_df(rows_data, headers):
        if not rows_data: return pd.DataFrame()
        matrix = [[cell.get('value', '') for cell in r.get('cells', [])] for r in rows_data]
        return pd.DataFrame(matrix, columns=headers, index=[r.get('row_index') for r in rows_data])

    def render_table(self, db, sheet_id, sheet_name):
        rows, headers = db.get_data_by_sheet_as_table(sheet_id)
        if rows:
            st.subheader(f"📊 Dữ liệu: {sheet_name}")
            df = self.build_df(rows, headers)
            search = st.text_input("🔍 Lọc nhanh dòng:", key="table_search")
            if search:
                df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            st.dataframe(df, width='stretch', height=500)
        else:
            st.info("Chưa có dữ liệu.")