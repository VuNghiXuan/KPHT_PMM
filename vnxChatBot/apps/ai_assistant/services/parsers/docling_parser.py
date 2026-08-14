import logging
from pathlib import Path
import pypdf  # Cần cài đặt: pip install pypdf
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions # Cần thêm OcrOptions
from docling.datamodel.base_models import InputFormat

logger = logging.getLogger(__name__)

class DoclingParser:
    """
    Parser thông minh có khả năng phân loại PDF:
    - PDF có layer text: Dùng native extraction (nhanh, chính xác).
    - PDF scan: Kích hoạt Force OCR (EasyOCR/Tesseract backend).
    """
    
    def __init__(self):
        # 1. Cấu hình cho PDF scan (OCR nặng)
        self.ocr_options = PdfPipelineOptions()
        self.ocr_options.do_ocr = True
        self.ocr_options.do_table_structure = True
        
        # 2. Cấu hình cho PDF có text (Nhanh)
        self.fast_options = PdfPipelineOptions()
        self.fast_options.do_ocr = False  # Bỏ qua OCR nếu có text gốc
        
        # 3. Converter tích hợp cả hai pipeline
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=self.ocr_options),
            }
        )

    def _is_scanned_pdf(self, file_path: str) -> bool:
        try:
            reader = pypdf.PdfReader(file_path)
            text = reader.pages[0].extract_text()
            return not text or len(text.strip()) < 10
        except Exception:
            return True

    def _get_converter(self, is_scan: bool) -> DocumentConverter:
        """Khởi tạo DocumentConverter với cấu hình OCR tiếng Việt chuẩn xác."""
        pipeline_options = PdfPipelineOptions()
        
        # Bật OCR hoàn toàn để xử lý cả file scan lẫn file text bị lỗi encoding/font
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        
        # Cấu hình OCR engine với ngôn ngữ tiếng Việt
        pipeline_options.ocr_options = RapidOcrOptions(lang=["vi"])
        
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )

    def parse(self, file_path: str):
        file_path_obj = Path(file_path)
        is_scan = self._is_scanned_pdf(str(file_path_obj))
        
        converter = self._get_converter(is_scan)

        try:
            logger.info(f"🔍 [DoclingParser] Mode: Forced-OCR | File: {file_path_obj.name}")
            
            result = converter.convert(str(file_path_obj))
            markdown_content = result.document.export_to_markdown()
            
            return [{
                "content": markdown_content,
                "metadata": {
                    "source_file": file_path_obj.name,
                    "is_scanned": is_scan,
                    "parser_type": "docling_forced_ocr"
                }
            }]
        except Exception as e:
            logger.error(f"❌ [DoclingParser Error] {file_path_obj.name}: {str(e)}")
            raise e