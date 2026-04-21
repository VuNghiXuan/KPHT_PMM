from config import Config
import json

class KnowledgeService:
    def __init__(self, db_manager, kv_manager, ai_agent=None):
        """
        Thằng này đứng giữa điều phối DB và Vector AI
        """
        self.db = db_manager
        self.kv = kv_manager
        self.ai_agent = ai_agent

    def process_new_sheet_labels(self, sheet_id):
        """
        Bóc nhãn từ DB -> Tính toán Vector -> Trả về danh sách từ mới/cũ
        """
        # 1. Lấy nhãn thô từ DB thông qua DBManager
        labels = self.db.extract_unique_labels(sheet_id)
        
        # 2. Mở session DB để đối soát
        session = self.db.get_session()
        try:
            # 3. Nhờ KnowledgeManager lọc xem từ nào lạ, từ nào quen
            analysis_report = self.kv.identify_new_knowledge(session, labels)
            return {"status": "success", "data": analysis_report}
        finally:
            session.close()

    def approve_and_learn(self, approved_list):
        """
        Lưu những gì Vũ đã định nghĩa vào DB
        """
        session = self.db.get_session()
        try:
            success = self.kv.commit_knowledge(session, approved_list)
            return success
        finally:
            session.close()
    
    def process_all_project_labels(self, project_id):
        """Quét tất cả nhãn của tất cả các sheet trong cùng 1 dự án"""
        # 1. Lấy tất cả nhãn độc nhất của cả dự án (không trùng lặp)
        all_labels = self.db.extract_unique_labels_by_project(project_id)
        
        session = self.db.get_session()
        try:
            # 2. Đối soát với kho tri thức
            analysis_report = self.kv.identify_new_knowledge(session, all_labels)
            
            # 3. Với những từ mới (NEW), gọi AI gợi ý định nghĩa luôn cho Vũ
            for item in analysis_report:
                if item['status'] == 'NEW':
                    # Gợi ý nhanh: Nếu Vũ để trống, AI Procedure sau này vẫn hiểu, 
                    # nhưng gợi ý ở đây giúp Vũ kiểm soát tốt hơn.
                    item['suggested_definition'] = self.ai_suggest_definition(item['term'])
            
            return analysis_report
        finally:
            session.close()

    def ai_suggest_definition(self, term):
        """Tự động gợi ý định nghĩa: Ưu tiên Config -> AI -> Trống"""
        if self.ai_agent:
            prompt = f"""
            Thuật ngữ: '{term}'
            Nhiệm vụ: 
            1. Định nghĩa ngắn gọn thuật ngữ này trong ngành vàng/phần mềm.
            2. Tạo ra 3 câu hỏi thực tế mà người dùng thường hỏi về thuật ngữ này.
            Trả về định dạng JSON: {{"definition": "...", "questions": ["q1", "q2", "q3"]}}
            """
            try:
                response = self.ai_agent.generate(prompt)
                # Logic parse JSON ở đây...
                return response
            except:
                pass
        return {"definition": "", "questions": []}
    
    

    def export_unlabeled_to_json(self, project_id):
        """Lọc các thuật ngữ NEW và chuyển thành chuỗi JSON"""
        # 1. Lấy báo cáo phân tích tri thức
        analysis_report = self.process_all_project_labels(project_id)
        
        # 2. Chỉ lọc những thằng 'NEW'
        unlabeled_data = [
            {
                "term": item['term'],
                "suggested_definition": item.get('suggested_definition', ''),
                "status": "NEW",
                "context": "HTJ Jewelry System"
            } 
            for item in analysis_report if item['status'] == 'NEW'
        ]
        
        # Trả về chuỗi JSON có format đẹp (indent=4)
        return json.dumps(unlabeled_data, indent=4, ensure_ascii=False)