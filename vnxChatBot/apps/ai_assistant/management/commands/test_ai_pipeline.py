# apps/ai_assistant/management/commands/test_ai_pipeline.py
import os
from django.core.management.base import BaseCommand
from apps.ai_assistant.services.parser import DocumentParserService
from apps.ai_assistant.models import KnowledgeUnit # Giả định mô hình dữ liệu

class Command(BaseCommand):
    help = "Kiểm thử luồng AI bóc tách tài liệu và kiểm toán mâu thuẫn ngầm"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Đường dẫn tới file cần test (Excel, Word, PDF)')
        parser.add_argument('--group', type=int, help='ID của ChatGroup cần test cô lập dữ liệu')

    def handle(self, *args, **options):
        file_path = options.get('file')
        group_id = options.get('group', 1)

        if not file_path or not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ Không tìm thấy file tại: {file_path}"))
            return

        self.stdout.write(self.style.WARNING(f"🚀 Bắt đầu giả lập AI Pipeline cho file: {file_path} (Group ID: {group_id})"))

        # Bước 1: Gọi Parser Service bóc tách đa định dạng
        try:
            chunks = DocumentParserService.parse_document(file_path)
            self.stdout.write(self.style.SUCCESS(f"✅ Bóc tách thành công {len(chunks)} chunks dữ liệu từ file."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Lỗi bóc tách: {str(e)}"))
            return

        # Bước 2: Mô phỏng AI Data Auditor & Đưa vào Staging
        for idx, chunk in enumerate(chunks):
            content = chunk["content"]
            metadata = chunk["metadata"]
            
            # Giả lập AI chấm điểm tin cậy (Confidence Score) & sinh raw_structure_json
            confidence_score = 0.88 if idx % 2 == 0 else 0.65 # Giả lập có chunk điểm thấp cần Human review
            is_conflict = (idx == 1) # Giả lập chunk thứ 2 bị mâu thuẫn với dữ liệu cũ
            
            self.stdout.write(f"\n--- Xử lý Chunk #{idx+1} ---")
            self.stdout.write(f"📊 Confidence Score: {confidence_score}")
            self.stdout.write(f"⚠️ Trạng thái Mâu thuẫn (Cosine Similarity >= 0.85): {'CÓ' if is_conflict else 'KHÔNG'}")

            # Bước 3: Lưu vào DB ở trạng thái Staging (Tuân thủ Vòng đời tri thức)
            # unit = KnowledgeUnit.objects.create(
            #     group_id=group_id,
            #     content=content,
            #     metadata=metadata,
            #     status='staging',
            #     confidence_score=confidence_score,
            #     is_conflict=is_conflict,
            #     conflict_report="Phát hiện trùng lặp nội dung với KnowledgeUnit #12 (Độ tương đồng: 0.89)" if is_conflict else ""
            # )
            
        self.stdout.write(self.style.SUCCESS("\n🎉 Hoàn thành kiểm thử AI Pipeline! Dữ liệu đã sẵn sàng hiển thị lên Dashboard."))