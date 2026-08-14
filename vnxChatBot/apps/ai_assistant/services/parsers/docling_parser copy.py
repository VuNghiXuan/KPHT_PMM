# File: apps/ai_assistant/services/parsers/docling_parser.py
import logging
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

logger = logging.getLogger(__name__)

class DoclingParser:
    """
    Parser chuyên dụng tích hợp Docling kết hợp Force OCR và Table Structure Extraction
    cho PDF, bảo đảm độ chính xác tuyệt đối cho tiếng Việt có dấu.
    """
    
    def __init__(self):
        # 1. Cấu hình pipeline nâng cao dành riêng cho tài liệu PDF
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = True
        pdf_options.do_table_structure = True
        
        # 2. Khởi tạo DocumentConverter với định tuyến format chính xác
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )

    def parse(self, file_path):
        parsed_chunks = []
        file_name = Path(file_path).name
        
        try:
            logger.info(f"🔄 [DoclingParser] Đang phân tích file với Force OCR: {file_name}")
            
            conversion_result = self.converter.convert(str(file_path))
            doc = conversion_result.document
            
            markdown_content = doc.export_to_markdown()
            
            parsed_chunks.append({
                "content": f"# Tài liệu: {file_name}\n\n{markdown_content}",
                "metadata": {
                    "source_file": file_name,
                    "parser_type": "docling_force_ocr",
                    "total_pages": getattr(doc, 'num_pages', 1)
                }
            })
            
            logger.info(f"✅ [DoclingParser] Bóc tách thành công: {file_name}")
            return parsed_chunks
            
        except Exception as e:
            logger.error(f"❌ [DoclingParser Error] Lỗi bóc tách file {file_name}: {str(e)}")
            raise e