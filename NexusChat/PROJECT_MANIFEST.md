# NexusChat Project Manifest

> *Cập nhật lần cuối: 16/Jul/26*

## 1. Hệ thống Modules (Apps)
- **accounting**: Chưa có mô tả nghiệp vụ
- **ai_assistant**: AI Brain, RAG Engine, tích hợp LLM và Vector Store.
- **core**: Nền tảng xác thực, quản lý Profile và Tenant (Company).
- **group_chat**: Quản lý ChatGroup, Membership và tin nhắn (WebSocket).
- **subscriptions**: Quản lý gói dịch vụ và phân quyền tính năng.
- **test_com_info**: Chưa có mô tả nghiệp vụ

## 2. Bản đồ Class & Luồng (Tự động hóa)

### App: accounting
#### File: `models.py`
- **Class Voucher**: Model Chứng từ kế toán (Phiếu thu, phiếu chi, hóa đơn...).
#### File: `views.py`

### App: ai_assistant
#### Mô tả chi tiết:
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

#### File: `models.py`
*File: apps/ai_assistant/models.py*
- **Class AIConfig**: Lưu trữ cấu hình AI (Provider, Key, Model) của người dùng hoặc nhóm.
- **Class Document**: Chưa có mô tả
#### File: `views.py`

### App: core
#### File: `models.py`
*Định nghĩa các Model nền tảng cho hệ thống Multi-tenant: User, Company và Profile.*
- **Class User**: Chưa có mô tả
- **Class Company**: Đại diện cho một đơn vị kinh doanh (Tenant).
- **Class CompanyManager**: Chưa có mô tả
- **Class CompanyScopedModel**: Abstract Model bắt buộc kế thừa cho mọi dữ liệu nghiệp vụ kế toán (Chứng từ, Sổ cái).
- **Class Profile**: Mở rộng thông tin người dùng. 
#### File: `views.py`

### App: group_chat
#### File: `models.py`
*File: apps/group_chat/models.py*
- **Class ChatGroup**: Class đại diện cho một nhóm chat riêng biệt.
- **Class Membership**: Class quản lý quyền của thành viên trong nhóm.
- **Class Message**: Chưa có mô tả
#### File: `views.py`

### App: subscriptions
#### File: `models.py`
*File: apps/subscriptions/models.py*
- **Class Feature**: Đại diện cho một tính năng/module cụ thể trong hệ thống.
- **Class SubscriptionPlan**: Định nghĩa các gói dịch vụ thương mại.
- **Class CompanySubscription**: Bản ghi liên kết Công ty với Gói dịch vụ đã đăng ký.
#### File: `views.py`
*File: apps/subscriptions/views.py*
- **Class SubscriptionListView**: Class hiển thị danh sách các gói dịch vụ có sẵn.

### App: test_com_info