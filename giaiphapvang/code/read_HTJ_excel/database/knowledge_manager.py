import os
import numpy as np
import json
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from .models import VectorKnowledge 

class KnowledgeManager:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        # Khởi tạo model một lần duy nhất
        self.model = SentenceTransformer(model_name)
        self.model.max_seq_length = 256
        print(f"🚀 KnowledgeManager: Loaded model {model_name}")

    
    def identify_new_knowledge(self, session, labels, threshold=0.85):
        """
        Đối soát nhãn mới - So sánh với kho tri thức hiện có để phân loại.
        Ngưỡng mặc định 0.85 để tránh nhận nhầm các thuật ngữ chuyên môn khác nhau.
        """
        # 1. Lấy toàn bộ kiến thức hiện có từ database
        known_records = session.query(VectorKnowledge).all()
        
        # Nếu kho tri thức trống hoặc không có nhãn đầu vào, mặc định tất cả là NEW
        if not known_records or not labels:
            return [{"term": l, "status": "NEW", "score": 0} for l in labels]

        # 2. Lọc các bản ghi đã được tạo embedding)
        valid_records = [r for r in known_records if r.embedding is not None]
        
        if not valid_records:
            return [{"term": l, "status": "NEW", "score": 0} for l in labels]

        known_texts = [r.main_term for r in valid_records]
        
        # 3. Chuyển đổi dữ liệu vector để tính toán toán học
        # Hỗ trợ cả 2 dạng: List (JSON mới) và Bytes (np.frombuffer cũ)
        known_embeddings = np.array([
                r.embedding for r in valid_records 
                if r.embedding is not None
            ])
        
        # 4. Vectorize danh sách nhãn mới cần đối soát từ Excel
        new_embeddings = self.model.encode(labels)
        
        # 5. Tính toán độ tương đồng Cosine giữa Nhãn mới và Kho tri thức cũ
        similarities = cosine_similarity(new_embeddings, known_embeddings)
        
        report = []
        # Cấu hình ngưỡng linh hoạt cho nghiệp vụ HTJ
        HIGH_CONFIDENCE = 0.95  # Chắc chắn là một (Gần như khớp chữ)
        
        for i, label in enumerate(labels):
            best_match_idx = np.argmax(similarities[i])
            max_score = similarities[i][best_match_idx]
            
            # TRƯỜNG HỢP 1: Thuật ngữ hoàn toàn mới (Score thấp hơn ngưỡng 0.85)
            # "Tiền công" và "Công gốc" thường rơi vào vùng này (~0.6 - 0.7) -> Sẽ được tạo mới
            if max_score < threshold:
                report.append({
                    "term": label, 
                    "status": "NEW", 
                    "match_with": None, 
                    "score": round(float(max_score), 2)
                })
            
            # TRƯỜNG HỢP 2: Nghi ngờ tương đồng (Vùng nhạy cảm: 0.85 - 0.95)
            # Hệ thống báo SIMILAR để anh Vũ kiểm tra lại xem có nên gom nhóm không
            elif max_score < HIGH_CONFIDENCE:
                report.append({
                    "term": label, 
                    "status": "SIMILAR", 
                    "match_with": known_texts[best_match_idx], 
                    "score": round(float(max_score), 2)
                })
            
            # TRƯỜNG HỢP 3: Đã tồn tại chắc chắn (Score > 0.95)
            # Hệ thống coi như đã biết, không cần định nghĩa lại
            else:
                report.append({
                    "term": label, 
                    "status": "EXISTS", 
                    "match_with": known_texts[best_match_idx], 
                    "score": round(float(max_score), 2)
                })
                
        return report

    def get_vector(self, text):
        'Lưu thành số đọc cho nhanh'
        if not text: return None
        # Khi dùng PickleType, anh nên trả về mảng Numpy thuần túy hoặc List.
        # Đừng ép kiểu sang string hay JSON, hãy để SQLAlchemy tự lo.
        return self.model.encode(text).tolist()

    def commit_knowledge(self, session, approved_list):
        """Lưu hoặc cập nhật tri thức - Đã sửa lỗi tên cột 'vector'"""
        for item in approved_list:
            if item.get('action') == 'skip': 
                continue
            
            term = item['term']
            # Tìm kiếm theo main_term
            existing = session.query(VectorKnowledge).filter_by(main_term=term).first()
            
            # Đóng gói tọa độ Excel
            source_meta = item.get('metadata', [])
            
            # CHÚ Ý: Key ở đây phải khớp 100% với tên cột trong Class VectorKnowledge
            data_fields = {
                "main_term": term,
                "definition": item.get('definition', ''),
                "synonyms": item.get('synonyms', ''),
                "business_rules": item.get('business_rules', ''),
                "logic_rules": item.get('logic_rules', ''),
                "sample_questions": item.get('questions', []), # Nếu Model dùng kiểu JSON, ko cần json.dumps
                "source_mapping": source_meta,
                "category": item.get('category', 'KHÁC').upper(), # AI tự phân loại
                "is_approved": 1,                
                "embedding": self.get_vector(item.get('definition', term))
            }

            if existing:
                for key, value in data_fields.items():
                    setattr(existing, key, value)
            else:
                # Không còn lỗi invalid keyword argument vì đã đổi 'embedding' -> 'vector'
                new_k = VectorKnowledge(**data_fields)
                session.add(new_k)
        
        try:
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ Lỗi Commit tại KnowledgeManager: {e}")
            return False

    def search_exact_answer(self, session, user_query, threshold=0.6):
        """Chatbot truy vấn tri thức - Trả về định nghĩa và vị trí trên Excel"""
        query_vec = self.model.encode([user_query])
        
        records = session.query(VectorKnowledge).filter(VectorKnowledge.embedding != None).all()
        if not records: return None
        
        known_embeddings = np.array([r.embedding for r in records])
        similarities = cosine_similarity(query_vec, known_embeddings)[0]
        best_idx = np.argmax(similarities)
        
        if similarities[best_idx] >= threshold:
            rec = records[best_idx]
            return {
                "term": rec.main_term,
                "answer": rec.definition,
                "score": round(float(similarities[best_idx]), 2),
                "category": rec.category,
                "mapping": json.loads(rec.source_mapping) if rec.source_mapping else [],
                "rules": rec.business_rules
            }
        return None

    def export_to_json(self, session, project_id, db_manager, file_path="storage/knowledge_backup.json"):
        """
        Xuất toàn bộ tri thức ra file JSON để backup.
        Đã tối ưu cho PickleType và khử ký tự lạ.
        """
        records = session.query(VectorKnowledge).all()
        data_to_export = []
        known_terms = set() 
        
        for r in records:
            known_terms.add(r.main_term)
            
            # Với PickleType, r.embedding đã là list/array, không dùng np.frombuffer
            vector_list = r.embedding if r.embedding is not None else []
            
            # Đưa vào danh sách xuất và dùng self.clean_data để làm sạch tiếng Việt
            entry = {
                "term": r.main_term,
                "definition": r.definition or "",
                "category": r.category or "VÀNG",
                "synonyms": r.synonyms or "",
                # source_mapping nếu lưu dạng JSON trong DB thì lấy thẳng, nếu String thì json.loads
                "source_mapping": r.source_mapping if isinstance(r.source_mapping, (list, dict)) else (json.loads(r.source_mapping) if r.source_mapping else []),
                "business_rules": r.business_rules or "",
                "logic_rules": r.logic_rules or "",
                "sample_questions": r.sample_questions if isinstance(r.sample_questions, list) else (json.loads(r.sample_questions) if r.sample_questions else []),
                "vector": vector_list,
                "status": "DEFINED"
            }
            # Làm sạch dữ liệu trước khi nạp vào danh sách xuất
            data_to_export.append(self.clean_data(entry))

        # Lấy thêm các nhãn chưa được định nghĩa từ database dự án
        all_labels = db_manager.extract_unique_labels_by_project(project_id)
        for label in all_labels:
            if label not in known_terms:
                data_to_export.append({
                    "term": label,
                    "definition": "CHƯA ĐỊNH NGHĨA",
                    "status": "DRAFT",
                    "source_mapping": []
                })

        # Xử lý đường dẫn
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                # ensure_ascii=False để đọc được tiếng Việt "Dẻ", "Cắt ni"...
                json.dump(data_to_export, f, ensure_ascii=False, indent=4, default=str)
            
            print(f"✅ [HTJ System] Đã xuất {len(data_to_export)} tri thức ra: {abs_path}")
            return True, abs_path, len(data_to_export)
        except Exception as e:
            print(f"❌ Lỗi khi xuất file JSON: {e}")
            return False, str(e), 0

    def import_from_json(self, session, file_path="storage/knowledge_backup.json"):
        """
        Import tri thức từ JSON - Tự động tái tạo Vector nếu bị thiếu.
        Đã khử lỗi bytes-like object bằng cách dùng thẳng List/Array với PickleType.
        """
        
        if not os.path.exists(file_path): 
            print(f"⚠️ File không tồn tại: {file_path}")
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data_import = json.load(f)
            
            count_new = 0
            count_update = 0

            for item in data_import:
                term = item.get('term', '').strip()
                # Bỏ qua nhãn trống hoặc nhãn nháp chưa định nghĩa
                if not term or item.get('status') == 'DRAFT': 
                    continue 

                exists = session.query(VectorKnowledge).filter_by(main_term=term).first()
                
                # 1. Xử lý Vector: Ưu tiên lấy từ file, không có thì gọi AI encode lại
                # KHÔNG dùng .tobytes(), cứ để dạng List/Array cho PickleType tự xử lý
                vector_data = item.get('vector')
                if not vector_data or len(vector_data) == 0:
                    vector_data = self.get_vector(term)
                
                # 2. Chuẩn bị dữ liệu (Làm sạch ký tự lạ lần nữa cho chắc)
                fields = {
                    "main_term": term,
                    "definition": item.get('definition', ''),
                    "category": item.get('category', 'KHÁC').upper(),
                    "synonyms": item.get('synonyms', ''),
                    # Lưu thẳng object/list vào cột JSON/PickleType, ko cần json.dumps thủ công
                    "source_mapping": item.get('source_mapping', []),
                    "business_rules": item.get('business_rules', ''),
                    "logic_rules": item.get('logic_rules', ''),
                    "sample_questions": item.get('sample_questions', []),
                    "embedding": vector_data,  # Đây là list tọa độ
                    "is_approved": 1
                }

                # 3. Tiến hành Lưu hoặc Cập nhật
                if not exists:
                    session.add(VectorKnowledge(**fields))
                    count_new += 1
                else:
                    for k, v in fields.items(): 
                        setattr(exists, k, v)
                    count_update += 1
            
            session.commit()
            print(f"✅ [HTJ System] Import thành công: Thêm mới {count_new}, Cập nhật {count_update}")
            return True

        except Exception as e:
            session.rollback()
            # Nếu dùng trong Streamlit thì st.error, nếu ko thì dùng print
            print(f"❌ Lỗi Import tri thức: {str(e)}")
            return False
    
    @classmethod  # Đổi từ staticmethod sang classmethod
    def clean_data(cls, data): # Thay data thành (cls, data)
        """Khử ký tự lạ..."""
        if isinstance(data, dict):
            # Dùng cls. để gọi đệ quy chính nó
            return {k: cls.clean_data(v) for k, v in data.items()} 
        elif isinstance(data, list):
            return [cls.clean_data(i) for i in data]
        elif isinstance(data, str):
            cleaned = data.replace('\u2028', '\n').replace('\u2029', '\n')
            return "".join(ch for ch in cleaned if ch.isprintable() or ch in "\n\r\t")
        return data