import os
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.ai_assistant.services.parser import DocumentParserService

class Command(BaseCommand):
    help = "Kiểm thử bóc tách tài liệu và tự động xuất kết quả ra file Markdown riêng"
    

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Đường dẫn tuyệt đối hoặc tương đối tới file cần test')
        parser.add_argument('--output', type=str, default='output_test.md', help='Tên hoặc đường dẫn file Markdown đầu ra (mặc định: output_test.md)')

    def handle(self, *args, **options):
        file_path = options.get('file')
        output_name = options.get('output')

        path_obj = Path(file_path)
        if not path_obj.exists():
            self.stdout.write(self.style.ERROR(f"❌ Không tìm thấy file tại đường dẫn: {file_path}"))
            return

        self.stdout.write(self.style.WARNING(f"🔄 Đang tiến hành bóc tách file: {path_obj.name}..."))

        try:
            # Gọi Service điều phối trung gian
            chunks = DocumentParserService.parse_document(file_path)
            
            self.stdout.write(self.style.SUCCESS(f"✅ Bóc tách thành công! Tổng số chunks thu được: {len(chunks)}\n"))

            # Gom toàn bộ nội dung content từ các chunks để xuất ra file Markdown
            full_markdown_content = ""
            for idx, chunk in enumerate(chunks, start=1):
                content = chunk.get('content', '')
                metadata = chunk.get('metadata', {})
                
                # In thông tin cấu trúc từng chunk ra console
                self.stdout.write(f"--- CHUNK #{idx} ---")
                self.stdout.write(f"📦 Metadata: {metadata}")
                self.stdout.write(f"📝 Nội dung Markdown (300 ký tự đầu):\n{content[:300]}...\n")
                self.stdout.write("-" * 40)
                
                # Gộp nội dung để ghi file
                full_markdown_content += f"\n\n<!-- --- CHUNK #{idx} --- -->\n\n" + content

            # Xác định đường dẫn lưu file đầu ra (cùng thư mục với file gốc hoặc thư mục hiện tại)
            output_path = path_obj.parent / output_name if not Path(output_name).is_absolute() else Path(output_name)
            
            # Ghi nội dung ra file Markdown riêng
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_markdown_content)

            self.stdout.write(self.style.SUCCESS(f"💾 Đã xuất toàn bộ kết quả Markdown thành công tại: {output_path}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi trong quá trình parse file: {str(e)}"))

# python manage.py test_document_parser --file "D:\ThanhVu\kpht\KPHT_PMM\vnxChatBot\data\QTrinh_MuaBanDoi_de.docx"
# python manage.py test_document_parser --file "data\66-bgddt.signed.pdf"
# python manage.py test_document_parser --file "data\Mota.xlsx"
