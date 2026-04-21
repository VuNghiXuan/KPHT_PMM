import os
import numpy as np
import json
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from .models_knowledge import VectorKnowledge # Giả định file model của Vũ

class KnowledgeManager:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        # Khởi tạo model một lần duy nhất khi tạo instance
        self.model = SentenceTransformer(model_name)
        print(f"🚀 KnowledgeManager: Loaded model {model_name}")

    def get_vector(self, text):
        """Chuyển văn bản thành bytes để lưu DB"""
        return self.model.encode(text).astype(np.float32).tobytes()

    def identify_new_knowledge(self, session, labels, threshold=0.3):
        """
        Đối soát danh sách nhãn mới với kho tri thức của HTJ Jewelry System.
        Hỗ trợ xử lý các bản ghi chưa có embedding để tránh lỗi NoneType.
        """
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        # 1. Lấy toàn bộ kiến thức hiện có từ DB
        known_records = session.query(VectorKnowledge).all()
        
        # Nếu DB trống, tất cả nhãn đều là mới
        if not known_records:
            return [{"term": l, "status": "NEW", "score": 0} for l in labels]

        # 2. Chuẩn bị Vector cũ - Chỉ lấy những bản ghi đã có embedding
        # Lọc bỏ các bản ghi vừa import mà chưa được vectorize để tránh lỗi np.frombuffer
        valid_records = [r for r in known_records if r.embedding is not None]
        
        # Nếu không có bản ghi nào có embedding (ví dụ: vừa mới import xong chưa chạy re-index)
        if not valid_records:
            return [{"term": l, "status": "NEW", "score": 0} for l in labels]

        known_texts = [r.question for r in valid_records]
        known_embeddings = np.array([
            np.frombuffer(r.embedding, dtype=np.float32) for r in valid_records
        ])
        
        # 3. Tính Vector cho danh sách labels mới gửi lên
        # Đảm bảo self.model.encode đã được khởi tạo (ví dụ: SentenceTransformer)
        new_embeddings = self.model.encode(labels)
        
        # 4. Tính ma trận tương đồng (Cosine Similarity)
        similarities = cosine_similarity(new_embeddings, known_embeddings)
        
        report = []
        for i, label in enumerate(labels):
            # Tìm bản ghi tương đồng nhất trong kho
            best_match_idx = np.argmax(similarities[i])
            max_score = similarities[i][best_match_idx]
            
            # PHÂN LOẠI TRẠNG THÁI:
            # Trường hợp 1: Nhãn hoàn toàn mới (độ tương đồng dưới ngưỡng threshold)
            if max_score < threshold:
                report.append({
                    "term": label,
                    "status": "NEW",
                    "match_with": None,
                    "score": round(float(max_score), 2)
                })
            
            # Trường hợp 2: Nhãn có sự tương đồng nhưng không khớp hoàn toàn (cần Vũ duyệt lại)
            elif max_score < 0.85: 
                report.append({
                    "term": label,
                    "status": "SIMILAR",
                    "match_with": known_texts[best_match_idx],
                    "score": round(float(max_score), 2)
                })
            
            # Trường hợp 3: Nếu max_score >= 0.85, hệ thống coi như đã tồn tại
            # Không thêm vào report để tránh làm phiền người quản lý (Vũ)
                    
        return report

    def commit_knowledge(self, session, approved_list):
        for item in approved_list:
            # Nếu Vũ đánh dấu là "Dùng từ cũ", đừng lưu thêm
            if item.get('action') == 'skip': continue
            
            # Kiểm tra tránh trùng lặp key_name
            existing = session.query(VectorKnowledge).filter_by(question=item['term']).first()
            if existing:
                existing.answer = item['definition'] # Cập nhật định nghĩa mới nhất
                existing.embedding = self.get_vector(item['term'])
            else:
                new_k = VectorKnowledge(
                    question=item['term'],
                    answer=item['definition'],
                    embedding=self.get_vector(item['term']),
                    category=item.get('category', 'GLOSSARY')
                )
                session.add(new_k)
        try:
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ Error committing knowledge: {e}")
            return False

    def search_exact_answer(self, session, user_query, threshold=0.6):
        """Dành riêng cho Chatbot truy vấn nhanh lời thoại/định nghĩa"""
        # Encode câu hỏi của khách
        query_vec = self.model.encode([user_query])
        
        # Lấy tất cả records (Có thể tối ưu bằng cách lấy theo category)
        records = session.query(VectorKnowledge).all()
        if not records: return None
        
        known_embeddings = np.array([np.frombuffer(r.embedding, dtype=np.float32) for r in records])
        
        # Tính tương đồng
        similarities = cosine_similarity(query_vec, known_embeddings)[0]
        best_idx = np.argmax(similarities)
        
        if similarities[best_idx] >= threshold:
            return {
                "answer": records[best_idx].answer,
                "score": similarities[best_idx],
                "category": records[best_idx].category
            }
        return None
    
    def export_to_context_text(self, session, category=None):
        """Chuyển kiến thức thành văn bản để nạp vào Prompt cho AI soạn quy trình"""
        query = session.query(VectorKnowledge)
        if category:
            query = query.filter_by(category=category)
        
        records = query.all()
        context = "DANH SÁCH THUẬT NGỮ VÀ QUY TẮC ĐÃ BIẾT:\n"
        for r in records:
            context += f"- {r.question}: {r.answer}\n"
        return context
    
    def export_to_json(self, session, file_path="storage/knowledge_backup.json"):
        """Xuất toàn bộ kho tri thức ra file JSON (kèm cả Vector)"""
        records = session.query(VectorKnowledge).all()
        data_to_export = []
        
        for r in records:
            # Chuyển bytes embedding sang list số thực để lưu được vào JSON
            vector_list = np.frombuffer(r.embedding, dtype=np.float32).tolist()
            data_to_export.append({
                "question": r.question,
                "answer": r.answer,
                "category": r.category,
                "vector": vector_list
            })
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_export, f, ensure_ascii=False, indent=4)
        print(f"💾 Đã xuất {len(data_to_export)} tri thức ra file: {file_path}")

    def import_from_json(self, session, file_path="storage/knowledge_backup.json"):
        import streamlit as st # Thêm để báo lỗi lên GUI
        
        if not os.path.exists(file_path):
            st.error(f"❌ Không tìm thấy file: {file_path}")
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data_import = json.load(f)
                
            count_added = 0
            count_skipped = 0
            
            for item in data_import:
                # 1. Trích xuất dữ liệu
                term = item.get('term', '').strip()
                suggested = item.get('suggested_definition', {})
                definition = suggested.get('definition', '').strip()
                questions_list = suggested.get('questions', [])
                question = (questions_list[0] if questions_list else term).strip()
                context = item.get('context', 'HTJ Jewelry System')

                if not question: continue # Bỏ qua nếu không có thuật ngữ

                # 2. Logic kiểm tra trùng thông minh hơn
                # Nếu định nghĩa trống, chỉ kiểm tra theo tên thuật ngữ (question)
                if not definition:
                    exists = session.query(VectorKnowledge).filter_by(question=question).first()
                else:
                    exists = session.query(VectorKnowledge).filter(
                        (VectorKnowledge.question == question) | 
                        (VectorKnowledge.answer == definition)
                    ).first()

                if not exists:
                    vector_bytes = None
                    # Nếu file có vector sẵn thì dùng, không thì để None chờ vectorize sau
                    if item.get('vector'):
                        vector_bytes = np.array(item['vector'], dtype=np.float32).tobytes()
                    
                    new_k = VectorKnowledge(
                        question=question,
                        answer=definition,
                        category=context,
                        embedding=vector_bytes
                    )
                    session.add(new_k)
                    count_added += 1
                else:
                    count_skipped += 1
            
            session.commit()
            
            if count_added > 0:
                st.success(f"🚀 Thành công: Thêm {count_added} mới, bỏ qua {count_skipped} trùng.")
                st.rerun() # Ép giao diện load lại dữ liệu mới
            else:
                st.warning(f"ℹ️ Không có dữ liệu mới nào được thêm (Trùng {count_skipped}).")
                
            return True

        except Exception as e:
            session.rollback()
            st.error(f"❌ Lỗi: {str(e)}")
            return False
    
    def check_exists(self, session, term):
        """Kiểm tra xem thuật ngữ đã tồn tại cứng trong DB chưa"""
        return session.query(VectorKnowledge).filter_by(question=term).first() is not None

    
# --- Khởi tạo instance dùng chung cho toàn app ---
# Vũ nên khởi tạo cái này một lần ở file main hoặc app.py
# kv_manager = KnowledgeManager()