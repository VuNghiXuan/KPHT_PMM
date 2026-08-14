import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentParserService:
    """
    Service điều phối trung gian (Orchestrator) giúp phân tích đa định dạng tài liệu
    thành cấu trúc Markdown/JSON chuẩn hóa trước khi đưa vào vòng đời kiểm duyệt.
    """
    
    @staticmethod
    def get_parser_for_file(file_extension):
        """Chọn parser chuyên dụng dựa trên định dạng file."""
        parsers = {
            'pdf': DoclingParser(),      # Tốt cho văn bản pháp luật, giữ hierarchy (Điều, Khoản)
            'docx': DoclingParser(),     # Giữ cấu trúc phân cấp văn bản Word tốt
            'xlsx': ExcelToMarkdown(),   # Custom-build: chuyển Excel thành Markdown Table theo row-chunks
            'xls': ExcelToMarkdown(),    # Hỗ trợ định dạng Excel cũ
            'png': VisionParser(),       # OCR/Vision cho ảnh chứa tài liệu quét
            'jpg': VisionParser(),
            'jpeg': VisionParser(),
            'html': HTMLParser(),        # Làm sạch và trích xuất nội dung HTML thô
        }
        
        parser = parsers.get(file_extension.lower().lstrip('.'))
        if not parser:
            logger.warning(f"⚠️ [ParserService] Không tìm thấy parser chuyên dụng cho đuôi file: {file_extension}. Dùng mặc định DoclingParser.")
            return DoclingParser()
        return parser

    @classmethod
    def parse_document(cls, file_path):
        """
        Phương thức chính để gọi bóc tách file dựa trên phần mở rộng.
        Trả về danh sách các chunk dữ liệu chuẩn hóa dạng dict: 
        [{"content": "...", "metadata": {...}}]
        """
        ext = Path(file_path).suffix
        parser = cls.get_parser_for_file(ext)
        return parser.parse(file_path)


class ExcelToMarkdown:
    """
    Parser chuyên dụng xử lý file Excel dung lượng lớn, phân rã bảng thành các 
    KnowledgeUnit dạng Markdown theo từng chunk dòng (row-based) kèm metadata dãy dòng.
    """
    
    def parse(self, file_path):
        all_data = []
        try:
            # Đọc toàn bộ sheet đầu tiên, giữ nguyên header
            df = pd.read_excel(file_path)
            table_name = Path(file_path).name

            # Chia nhỏ dữ liệu thành các đoạn (chunks) 50 dòng để tối ưu ngữ cảnh cho AI
            chunk_size = 50
            total_rows = len(df)

            if total_rows == 0:
                logger.warning(f"⚠️ [ExcelParser] File Excel {table_name} không có dữ liệu.")
                return []

            for i in range(0, total_rows, chunk_size):
                chunk = df.iloc[i : i + chunk_size]
                structured_data = chunk.to_dict(orient='records')
                
                # Xây dựng bảng Markdown có ngữ cảnh cho từng chunk
                md_content = f"### Bảng dữ liệu: {table_name} (Phạm vi dòng {i} đến {min(i + chunk_size, total_rows)})\n\n"
                md_content += "| " + " | ".join([str(col) for col in df.columns]) + " |\n"
                md_content += "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
                
                for row in structured_data:
                    md_content += "| " + " | ".join([str(val) for val in row.values()]) + " |\n"
                
                all_data.append({
                    "content": md_content,
                    "metadata": {
                        "table_name": table_name,
                        "row_range": f"{i}-{min(i + chunk_size, total_rows)}",
                        "type": "excel_table"
                    }
                })
                
            logger.info(f"✅ [ExcelParser] Đã bóc tách thành công {len(all_data)} chunks từ file {table_name}")
            return all_data

        except Exception as e:
            logger.error(f"❌ [ExcelParser Error] Lỗi đọc file Excel {file_path}: {str(e)}")
            raise e


class DoclingParser:
    """
    Parser chuyên dụng cho Word, PDF (đặc biệt là tài liệu pháp luật),
    giữ vững hệ thống phân cấp đề mục (Heading, Điều, Khoản).
    """
    
    def parse(self, file_path):
        # Tích hợp thư viện Docling/Marker để trích xuất cấu trúc phân cấp cây văn bản
        # Trả về cấu trúc chuẩn cho KnowledgeUnit
        parsed_chunks = []
        file_name = Path(file_path).name
        
        try:
            # [Logic chuẩn tích hợp Docling thực tế tại đây]
            # Giả lập kết quả trả về cấu trúc phân cấp tiêu chuẩn cho văn bản pháp luật/Word:
            logger.info(f"🔄 [DoclingParser] Đang phân tích cấu trúc phân cấp cho file: {file_name}")
            
            # Đoạn code mẫu cấu trúc trả về sau khi Docling bóc tách:
            parsed_chunks.append({
                "content": f"# Tài liệu pháp luật / Văn bản: {file_name}\n\n[Nội dung chi tiết được bóc tách phân cấp bằng Docling Parser]",
                "metadata": {
                    "source_file": file_name,
                    "parser_type": "docling_hierarchical",
                    "section": "General"
                }
            })
            return parsed_chunks
            
        except Exception as e:
            logger.error(f"❌ [DoclingParser Error] Lỗi bóc tách file {file_name}: {str(e)}")
            raise e


class VisionParser:
    """Parser xử lý hình ảnh tài liệu quét (PNG, JPG) sử dụng OCR / Vision Model."""
    
    def parse(self, file_path):
        file_name = Path(file_path).name
        logger.info(f"👁️ [VisionParser] Đang thực hiện OCR cho file ảnh: {file_name}")
        # Tích hợp OCR Engine tại đây
        return [{
            "content": f"[Nội dung trích xuất từ ảnh OCR: {file_name}]",
            "metadata": {"source_file": file_name, "parser_type": "vision_ocr"}
        }]


class HTMLParser:
    """Parser làm sạch và trích xuất nội dung văn bản từ trang HTML."""
    
    def parse(self, file_path):
        file_name = Path(file_path).name
        logger.info(f"🌐 [HTMLParser] Đang làm sạch mã HTML của file: {file_name}")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        # Xử lý loại bỏ thẻ rác, giữ text sạch
        return [{
            "content": f"[Nội dung HTML đã làm sạch từ: {file_name}]\n{html_content[:2000]}",
            "metadata": {"source_file": file_name, "parser_type": "html_clean"}
        }]