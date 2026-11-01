import logging
from .models import ExcelTableRegion, DataField

logger = logging.getLogger(__name__)

class ExcelRegionAnalyzer:
    """
    Module chuyên trách phân tích cấu trúc tọa độ ô của anh Vũ.
    Nhiệm vụ: Gom nhóm các hạt cát (DataField) rời rạc thành các cụm Vùng Nghiệp Vụ (ExcelTableRegion) có nghĩa.
    """
    
    @staticmethod
    def cluster_and_bind_regions(sheet_obj):
        """
        Quét toàn bộ DataField của Sheet để tự động nhận diện và tạo Vùng nghiệp vụ.
        """
        try:
            # 1. Lấy tất cả DataField thuộc Sheet hiện tại
            fields = DataField.objects.filter(sheet=sheet_obj)
            if not fields.exists():
                return
                
            # Dọn dẹp các vùng cũ của sheet này để phân tích lại từ đầu (tránh rác)
            ExcelTableRegion.objects.filter(sheet=sheet_obj).delete()

            # --- THUẬT TOÁN GOM CỤM TỰ ĐỘNG BẰNG QUY ƯỚC CỦA ANH VŨ ---
            # Gom các ô dựa trên loại dữ liệu nghiệp vụ chính và logic
            logic_fields = [f for f in fields if f.field_type == 'LOGIC']
            data_fields = [f for f in fields if f.field_type == 'DATA']
            
            # Khởi tạo danh sách các vùng phát hiện được
            detected_regions = []

            # Trường hợp 1: Nếu sheet có công thức tính toán (Tiệm vàng thường dùng bảng tính)
            if logic_fields:
                # Tìm biên tọa độ (Min/Max Row và Col) của khối logic tính toán
                rows = [int(''.join(filter(str.isdigit, f.cell_address))) for f in logic_fields]
                cols = [''.join(filter(str.isalpha, f.cell_address)) for f in logic_fields]
                
                if rows:
                    min_row, max_row = min(rows), max(rows)
                    # Giới hạn vùng bao quanh khối công thức (mở rộng thêm 2 dòng tiêu đề phía trên)
                    start_row = max(1, min_row - 2)
                    coord_range = f"A{start_row}:Z{max_row + 1}"
                    
                    # Tạo Vùng Logic tính toán
                    logic_region = ExcelTableRegion.objects.create(
                        sheet=sheet_obj,
                        name=f"Khối tính toán & Công thức ({sheet_obj.name})",
                        coordinates=coord_range,
                        region_type='CALCULATION_BLOCK'
                    )
                    detected_regions.append(logic_region)

            # Trường hợp 2: Nếu không có công thức nhưng có nhiều trường dữ liệu (Dạng Form điền thông tin)
            if not detected_regions and data_fields:
                form_region = ExcelTableRegion.objects.create(
                    sheet=sheet_obj,
                    name=f"Form nghiệp vụ tổng hợp ({sheet_obj.name})",
                    coordinates=f"A1:G{max(len(data_fields) // 3, 10)}",
                    region_type='FORM'
                )
                detected_regions.append(form_region)

            # --- BƯỚC MẤU CHỐT: GẮN ID VÙNG VÀO TỪNG DATAFIELD ---
            # Duyệt qua các vùng vừa tạo và cập nhật mối quan hệ cho các ô nằm trong tọa độ đó
            for region in detected_regions:
                # Tạm thời map toàn bộ các DataField loại DATA và LOGIC vào vùng nghiệp vụ chính vừa tìm được
                fields_to_bind = fields.filter(field_type__in=['DATA', 'LOGIC'])
                fields_to_bind.update(region=region)
                
            logger.info(f"⚡ [Analyzer] Đã gom cụm và đồng bộ xong {len(detected_regions)} vùng nghiệp vụ cho Sheet: {sheet_obj.name}")
            
        except Exception as e:
            logger.error(f"Lỗi phân tích gom cụm vùng Excel: {str(e)}")

    @staticmethod
    def refine_regions_by_ai_manifest(sheet_obj, ai_json_manifest):
        """
        Hàm mở rộng: Nhận diện vùng chính xác tuyệt đối bằng bản đồ cấu trúc do AI trả về.
        (Sẽ được gọi sau khi luồng AI tinh chế chạy xong và xuất ra file JSON dạng map tọa độ).
        """
        try:
            if not ai_json_manifest or not isinstance(ai_json_manifest, list):
                return
                
            for block in ai_json_manifest:
                name = block.get("vung_nghiep_vu")
                coords = block.get("toa_do")  # Ví dụ: "B2:F20"
                r_type = block.get("loại_vùng", "FORM")
                
                if name and coords:
                    region, created = ExcelTableRegion.objects.update_or_create(
                        sheet=sheet_obj,
                        coordinates=coords,
                        defaults={'name': name, 'region_type': r_type}
                    )
                    # Quét các ô chi tiết nằm trong dải tọa độ này để gắn khóa ngoại
                    # (Có thể viết thêm hàm helper check_cell_in_range nếu anh cần bóc tách siêu chi tiết)
        except Exception as e:
            logger.error(f"Lỗi tinh chế vùng bằng AI: {str(e)}")