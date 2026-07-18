# VnxChatBot Project Manifest

> *Cập nhật: 18/Jul/26*

## 1. Hệ thống Modules (Apps)
- **ai_assistant**: Bộ não AI, RAG Engine, Vector Store và LLM Service.
- **arch_manager**: Kho lưu trữ kiến trúc, sơ đồ và luồng hệ thống.
- **group_chat**: Quản lý Nhóm, Thành viên, Tài liệu và Feedback.
- **subscriptions**: Quản lý gói dịch vụ và giới hạn thành viên theo Group.

## 2. Bản đồ Class & Luồng (Tự động hóa)

### App: ai_assistant
#### File: `models.py`
*Mục đích: Quản lý cấu hình AI riêng biệt cho từng nhóm.*
- **Class GroupAIProvider**: Cấu hình Provider riêng cho từng nhóm (Group-Centric).
#### File: `signals.py`
*File: apps/ai_assistant/signals.py*

### App: arch_manager
#### File: `models.py`
*Mục đích: Lưu trữ sơ đồ kiến trúc, luồng nghiệp vụ và trạng thái hệ thống.*
- **Class SystemBlueprint**: Lưu trữ các phiên bản của bản đồ kiến trúc hệ thống.

### App: group_chat
#### File: `models.py`
*Mục đích: Định nghĩa các thực thể cốt lõi cho Nhóm làm việc và Vòng đời tri thức.*
- **Class ChatGroup**: Đại diện cho một nhóm làm việc độc lập. Mọi dữ liệu (tài liệu, tin nhắn, kiến thức) đều thuộc về nhóm này.
- **Class Membership**: Quản lý thành viên trong nhóm.
- **Class Document**: Lưu trữ file gốc người dùng tải lên, phục vụ cho việc trích xuất tri thức.
- **Class KnowledgeUnit**: Đơn vị kiến thức trích xuất từ Document.
#### File: `signals.py`
*Mục đích: Tự động hóa các tác vụ ngầm thông qua Django Signals.*

### App: subscriptions
#### File: `models.py`
*Mục đích: Quản lý gói cước và giới hạn thành viên cho từng ChatGroup.*
- **Class Subscription**: Quản lý trạng thái và giới hạn của nhóm.
#### File: `signals.py`
*Mục đích: Tự động khởi tạo gói dịch vụ cho nhóm mới.*