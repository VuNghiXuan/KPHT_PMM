"""
Mục đích: Engine lõi thực hiện trích xuất tri thức và chấm điểm tin cậy (Confidence Score).
Tác giả: Kiến trúc sư VnxChatBot
"""
from .services.ai_factory import AIFactory

class AI_Engine:
    
    @staticmethod
    def extract_and_score(file_path, group=None):
        """
        Trích xuất nội dung và gán điểm tin cậy (0.0 - 1.0).
        """
        # 1. Trích xuất text thô từ file (placeholder cho logic xử lý file của bạn)
        raw_text = AI_Engine._extract_text(file_path)
        
        if len(raw_text) < 50:
            return "Dữ liệu quá ngắn hoặc không thể đọc", 0.0
            
        # 2. Sử dụng Factory để gọi LLM theo cấu hình nhóm
        prompt = f"""
        Phân tích nội dung sau và trả về kết quả định dạng JSON:
        {{
            "content": "Nội dung tóm tắt sạch sẽ",
            "confidence": 0.0 - 1.0
        }}
        Nội dung tài liệu: {raw_text[:2000]}
        """
        
        response = AIFactory.get_service_for_group(group, prompt)
        
        # 3. Parse kết quả từ LLM
        return AI_Engine._parse_llm_response(response)

    @staticmethod
    def _extract_text(file_path):
        """Helper tách text dựa trên đuôi file."""
        # TODO: Triển khai logic đọc file PDF/DOCX tại đây
        return "Nội dung giả lập từ tài liệu"

    @staticmethod
    def _parse_llm_response(response):
        """Làm sạch và lấy giá trị từ response của LLM."""
        # Logic này sẽ trả về tuple (content, confidence)
        # Trong thực tế, bạn sẽ dùng json.loads(response)
        return "Nội dung đã được AI trích xuất", 0.95