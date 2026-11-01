# import numpy as np
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity

# # Tải model (Lần đầu sẽ hơi lâu, sau đó nó chạy offline hoàn toàn)
# # Model này hỗ trợ tiếng Việt rất tốt và cực nhẹ
# model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# def get_embedding(text):
#     return model.encode(text).tobytes()

# def find_best_match(new_term, db_records):
#     """
#     So sánh từ mới với tất cả 'question' trong DB
#     """
#     if not db_records:
#         return None, 0

#     # Chuyển từ mới thành vector
#     new_vec = model.encode([new_term])
    
#     best_match = None
#     max_score = 0

#     for record in db_records:
#         # Chuyển vector từ bytes trong DB ngược lại thành numpy array
#         db_vec = np.frombuffer(record.embedding, dtype=np.float32).reshape(1, -1)
        
#         # Tính Cosine Similarity (kết quả từ 0 đến 1)
#         score = cosine_similarity(new_vec, db_vec)[0][0]
        
#         if score > max_score:
#             max_score = score
#             best_match = record

#     return best_match, max_score