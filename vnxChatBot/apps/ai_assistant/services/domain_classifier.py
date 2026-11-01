# apps/ai_assistant/services/domain_classifier.py

from typing import Optional
import numpy as np
from ..models.domain import DomainCategory
from .ai_engine import AIEngineService


def classify_text_domain(
    chunk_text: str, chunk_embedding: list = None
) -> Optional[DomainCategory]:
    """Phân loại chunk vào Domain phù hợp dựa trên Cosine Similarity."""
    domains = list(
        DomainCategory.objects.filter(
            is_active=True, embedding__isnull=False
        )
    )
    if not domains:
        return None

    # Nếu chưa truyền embedding của chunk vào thì tự lấy bằng AIEngineService
    if chunk_embedding is None:
        chunk_embedding = AIEngineService.get_embedding(chunk_text)

    # 1. Chuyển Vector chunk và ma trận Vector domain sang Numpy Array
    chunk_vec = np.array(chunk_embedding, dtype=np.float32)
    domain_matrix = np.array([d.embedding for d in domains], dtype=np.float32)

    # 2. Tính Cosine Similarity hàng loạt
    chunk_norm = np.linalg.norm(chunk_vec)
    domain_norms = np.linalg.norm(domain_matrix, axis=1)

    similarities = np.dot(domain_matrix, chunk_vec) / (
        domain_norms * chunk_norm + 1e-8
    )

    # 3. Tìm chỉ số Domain có điểm cao nhất
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])
    best_domain = domains[best_idx]

    # 4. Kiểm tra ngưỡng độ tương đồng
    if best_score >= best_domain.similarity_threshold:
        return best_domain

    return None