# Module: AI Assistant (The Brain)

## Luồng xử lý dữ liệu (AI Flow)
Luồng chính: `ChatGroup` -> `VectorDB` (RAG) -> `LLM` -> `Message`.

### Các thành phần cốt lõi:
- **`services/rag_engine.py`**: Điểm tiếp nhận yêu cầu, truy vấn dữ liệu từ `VectorDB` dựa trên `ChatGroup` hiện tại.
- **`services/llm_provider.py`**: Cổng kết nối với các mô hình LLM (OpenAI, Claude, v.v.).
- **`models.py`**: Quản lý tài liệu (`Document`) và cấu hình (`AIConfig`) theo phạm vi từng nhóm.

### Nguyên tắc thiết kế (Group-Centric):
1. **Cô lập kiến thức:** Tài liệu của nhóm nào chỉ phục vụ truy vấn cho nhóm đó (dựa trên `ForeignKey` tới `ChatGroup`).
2. **Tự động hóa:** AI phải phản hồi dựa trên ngữ cảnh đã được RAG cung cấp.