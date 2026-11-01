# Đường dẫn: ./src/calculator.py
# Mục đích: Backend tính toán tự động, chuẩn hóa dữ liệu số và áp dụng công thức suy luận kho vàng bạc.

import pandas as pd

class GoldCalculator:
    """
    Lớp xử lý logic tính toán, làm sạch dữ liệu số và suy luận trọng lượng/giá thành.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def clean_numbers(self):
        numeric_cols = [
            "Số lượng", "Tổng cân", "TL Hột", "TL vàng nhận về", "TL Vàng gia công", 
            "Quy 999", "Tỷ giá", "Thành tiền", "Đơn giá công/món", "Tổng tiền Công", 
            "Tổng Công có VAT", "TỔNG GIÁ THÀNH", "Tỷ lệ hao hụt"
        ]
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(
                    self.df[col].astype(str).str.replace(r'[^\d.,-]', '', regex=True).str.replace(',', '.'), 
                    errors='coerce'
                ).fillna(0.0)

    def apply_rules(self):
        self.clean_numbers()
        processed = []
        for _, row in self.df.iterrows():
            r = row.to_dict()
            tong_can = float(r.get("Tổng cân", 0.0))
            tl_hot = float(r.get("TL Hột", 0.0))
            tl_nhan = float(r.get("TL vàng nhận về", 0.0))
            thanh_tien = float(r.get("Thành tiền", 0.0))
            tong_cong_vat = float(r.get("Tổng Công có VAT", 0.0))
            tong_gia = float(r.get("TỔNG GIÁ THÀNH", 0.0))

            # Suy luận TL vàng nhận về = Tổng cân - TL hột
            if tl_nhan == 0.0 and tong_can > 0.0:
                r["TL vàng nhận về"] = max(0.0, tong_can - tl_hot)

            # Suy luận Tổng giá thành = Thành tiền vàng + Tổng công có VAT
            if tong_gia == 0.0:
                r["TỔNG GIÁ THÀNH"] = thanh_tien + tong_cong_vat

            processed.append(r)

        self.df = pd.DataFrame(processed)
        return self.df

def process_calculation(df_input: pd.DataFrame) -> pd.DataFrame:
    if df_input is None or df_input.empty:
        return pd.DataFrame()
    calc = GoldCalculator(df_input)
    return calc.apply_rules()