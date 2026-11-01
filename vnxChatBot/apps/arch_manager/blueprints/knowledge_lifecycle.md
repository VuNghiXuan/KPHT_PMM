# State Machine: Knowledge Lifecycle

## Trạng thái
- **PENDING**: Mặc định sau khi trích xuất. Chưa tồn tại trong Vector DB.
- **APPROVED**: Sau khi Admin duyệt. Kích hoạt `RAGEngine.add_knowledge()`.
- **ROLLBACK**: Sau khi Admin hủy. Kích hoạt `RAGEngine.remove_knowledge()`.

## Logic Chuyển đổi (Transitions)
1. `PENDING` -> `APPROVED`:
   - Trigger: Admin update `status`='approved'.
   - Action: Ghi bản ghi vào Vector DB kèm metadata `group_id`.
2. `APPROVED` -> `ROLLBACK`:
   - Trigger: Admin update `status`='rollback'.
   - Action: Gọi `delete()` trong Vector DB bằng `id`.