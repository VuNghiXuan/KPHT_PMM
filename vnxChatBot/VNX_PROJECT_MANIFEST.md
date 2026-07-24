# VnxChatBot Project Manifest

> *Cập nhật tự động: 21/Jul/26*

> *Tài liệu này phản ánh chính xác cấu trúc thư mục, tệp tin, Class và Hàm thực tế của mã nguồn (Living Architecture).*

## 1. Hệ thống Modules (Apps)
- **ai_assistant**: Bộ não AI, RAG Engine, Vector Store và LLM Service (AIFactory).
- **arch_manager**: Kho lưu trữ kiến trúc, sơ đồ tự động nội soi và KnowledgeUnit.
- **core**: Nền tảng hệ thống (User, Profile, Auth cơ bản).
- **group_chat**: Quản lý Nhóm, Thành viên, Tài liệu, Vòng đời tri thức và Feedback.
- **subscriptions**: Quản lý gói dịch vụ và giới hạn thành viên theo ChatGroup.

## 2. Cây Cấu trúc Thư mục & Chi tiết Class/Hàm (Introspection)

### App: `ai_assistant`
> *Mô tả:* Bộ não AI, RAG Engine, Vector Store và LLM Service (AIFactory).

#### 📂 Cấu trúc thư mục & tệp tin:
  ├── 📄 `README.md`
  ├── 📄 `__init__.py`
  ├── 📄 `admin.py`
  ├── 📄 `apps.py`
  ├── 📄 `engine.py`
  ├── 📄 `file_processor.py`
  ├── 📄 `forms_AI_keys.py`
  ├── 📄 `models.py`
  ├── 📁 **services/**
  │   ├── 📄 `__init__.py`
  │   ├── 📄 `ai_factory.py`
  │   ├── 📄 `ai_processor_service.py`
  │   ├── 📄 `document_processor.py`
  │   ├── 📄 `llm_provider.py`
  │   ├── 📄 `notification.py`
  │   └── 📄 `rag_engine.py`
  ├── 📄 `signals.py`
  ├── 📄 `tasks.py`
  ├── 📁 **tests/**
  │   └── 📄 `test_signals.py`
  ├── 📄 `tests.py`
  ├── 📁 **vector_store/**
  │   ├── 📄 `__init__.py`
  │   └── 📄 `chromadb_client.py`
  └── 📄 `views.py`

#### 🔍 Phân tích chi tiết mã nguồn (AST):
- **File: `models.py`**
  > *Mô tả:* Mục đích: Quản lý cấu hình AI riêng biệt cho từng nhóm.
  - **Class `GroupAIProvider`**: Cấu hình Provider riêng cho từng nhóm (Group-Centric).
    - *Method `__str__()`*: Hàm xử lý nội bộ
- **File: `signals.py`**
  > *Mô tả:* Module: ai_assistant.signals
  - **Function `process_document_to_vector()`**: Lắng nghe sự kiện khi một Document mới được tải lên nhóm.
  - **Function `remove_document_from_vector()`**: Dọn dẹp VectorDB khi một Document bị xóa hoàn toàn khỏi hệ thống,
  - **Function `handle_knowledge_unit_lifecycle()`**: Lắng nghe thay đổi trạng thái của KnowledgeUnit (Knowledge Lifecycle).
  - **Function `handle_knowledge_unit_cleanup()`**: Xóa sạch embedding liên quan trong Vector Store ngay trước khi 
  - **Function `create_default_chat_group_for_new_user()`**: Tự động khởi tạo Nhóm làm việc riêng và phân quyền Admin cho User mới đăng ký,
- **File: `views.py`**
  > *Mô tả:* Mục đích: Cung cấp API/Dashboard cho Admin xem danh sách kiến thức đã duyệt.
  - **Function `knowledge_dashboard()`**: View trả về danh sách kiến thức đã duyệt của nhóm.
- **File: `apps.py`**
  > *Mô tả:* File: apps/ai_assistant/apps.py
  - **Class `AiAssistantConfig`**: Chưa có mô tả Class
    - *Method `ready()`*: Hàm xử lý nội bộ
- **File: `admin.py`**
  - **Class `GroupAIProviderAdmin`**: Chưa có mô tả Class
- **File: `engine.py`**
  > *Mô tả:* Mục đích: Engine lõi thực hiện trích xuất tri thức và chấm điểm tin cậy (Confidence Score).
  - **Class `AI_Engine`**: Chưa có mô tả Class
    - *Method `extract_and_score()`*: Trích xuất nội dung và gán điểm tin cậy (0.0 - 1.0).
    - *Method `_extract_text()`*: Helper tách text dựa trên đuôi file.
    - *Method `_parse_llm_response()`*: Làm sạch và lấy giá trị từ response của LLM.
- **File: `file_processor.py`**
  > *Mô tả:* Mục đích: Trích xuất text từ đa dạng định dạng file (docx, xlsx, csv, pdf, hình ảnh, txt).
  - **Class `FileProcessor`**: Service trích xuất text tập trung.
    - *Method `process_txt()`*: Hàm xử lý nội bộ
    - *Method `process_docx()`*: Hàm xử lý nội bộ
    - *Method `process_excel()`*: Hàm xử lý nội bộ
    - *Method `process_csv()`*: Xử lý file CSV.
    - *Method `process_pdf()`*: Trích xuất text từ PDF sử dụng PyMuPDF.
    - *Method `process_image()`*: Hàm xử lý nội bộ
  - **Function `extract_text_from_file()`**: Điều hướng xử lý file đa định dạng.
- **File: `forms_AI_keys.py`**
  > *Mô tả:* File: apps/ai_assistant/forms.py
  - **Class `AIConfigForm`**: Chưa có mô tả Class
- **File: `tasks.py`**
  - **Function `process_document_task()`**: Task ngầm xử lý tài liệu khi có file upload mới.
- **File: `tests.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `__init__.py`**
  - *(File trống hoặc không chứa Class/Function)*

### App: `arch_manager`
> *Mô tả:* Kho lưu trữ kiến trúc, sơ đồ tự động nội soi và KnowledgeUnit.

#### 📂 Cấu trúc thư mục & tệp tin:
  ├── 📄 `__init__.py`
  ├── 📄 `admin.py`
  ├── 📄 `apps.py`
  ├── 📁 **blueprints/**
  │   ├── 📄 `knowledge_lifecycle.md`
  │   └── 📄 `v1.md`
  ├── 📄 `models.py`
  ├── 📄 `tests.py`
  ├── 📄 `urls.py`
  ├── 📄 `utils.py`
  └── 📄 `views.py`

#### 🔍 Phân tích chi tiết mã nguồn (AST):
- **File: `models.py`**
  > *Mô tả:* Module: arch_manager.models
  - **Class `SystemBlueprint`**: Class: SystemBlueprint
    - *Method `__str__()`*: Hàm xử lý nội bộ
    - *Method `generate_dynamic_erd()`*: Tự động nội soi 100%: Quét toàn bộ apps, models và thể hiện rõ mối quan hệ 1-n (Multiplicity).
- **File: `views.py`**
  > *Mô tả:* Module: arch_manager.views
  - **Class `SystemBlueprintView`**: Class: SystemBlueprintView
    - *Method `get()`*: Xử lý phương thức GET, gọi engine sinh sơ đồ và in log debug chi tiết 
  - **Function `approve_system_blueprint()`**: Function: approve_system_blueprint
- **File: `apps.py`**
  - **Class `ArchManagerConfig`**: Chưa có mô tả Class
- **File: `admin.py`**
  > *Mô tả:* Module: arch_manager.admin
  - **Class `SystemBlueprintAdmin`**: Tùy chỉnh giao diện quản trị cho SystemBlueprint, giúp quản trị viên 
    - *Method `view_architecture_btn()`*: Tạo nút bấm mở trang Living Documentation ngoài danh sách admin.
    - *Method `view_architecture_readonly()`*: Tạo nút bấm mở trang Living Documentation trong form chi tiết.
    - *Method `save_model()`*: Đảm bảo chỉ có 1 bản ghi active tại một thời điểm.
- **File: `urls.py`**
  > *Mô tả:* Module: arch_manager.urls
  - *(File trống hoặc không chứa Class/Function)*
- **File: `tests.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `utils.py`**
  > *Mô tả:* Module: arch_manager.utils
  - **Class `ArchitectureIntrospectionEngine`**: Class: ArchitectureIntrospectionEngine
    - *Method `generate_erd()`*: Sinh sơ đồ ERD (Entity Relationship Diagram) tập trung xoay quanh ChatGroup (Group-Centric).
    - *Method `generate_code_flow()`*: Sinh sơ đồ luồng dữ liệu (Code Flow) từ Upload đến LLM RAG Pipeline.
    - *Method `generate_state_machine()`*: Sinh sơ đồ trạng thái (Knowledge Lifecycle State Machine) cho KnowledgeUnit.
    - *Method `generate_component_diagram()`*: Sinh sơ đồ kiến trúc phân hệ theo mô hình Modular Monolith của VnxChatBot.
- **File: `__init__.py`**
  - *(File trống hoặc không chứa Class/Function)*

### App: `core`
> *Mô tả:* Nền tảng hệ thống (User, Profile, Auth cơ bản).

#### 📂 Cấu trúc thư mục & tệp tin:
  ├── 📄 `__init__.py`
  ├── 📄 `admin.py`
  ├── 📄 `apps.py`
  ├── 📄 `context_processors.py`
  ├── 📄 `decorators.py`
  ├── 📄 `forms_profile_customer.py`
  ├── 📄 `forms_register.py`
  ├── 📄 `models.py`
  ├── 📄 `tests.py`
  ├── 📄 `urls.py`
  ├── 📄 `views.py`
  ├── 📄 `views_dev copy.py`
  └── 📄 `views_dev.py`

#### 🔍 Phân tích chi tiết mã nguồn (AST):
- **File: `models.py`**
  > *Mô tả:* Mục đích: Định nghĩa User và Profile cho vnxChatBot.
  - **Class `User`**: User model tùy chỉnh cho vnxChatBot.
  - **Class `Profile`**: Mở rộng thông tin người dùng.
    - *Method `__str__()`*: Hàm xử lý nội bộ
- **File: `views.py`**
  > *Mô tả:* Mục đích: Xử lý xác thực người dùng và điều hướng chính.
  - **Function `register_view()`**: Đăng ký người dùng mới. Sau khi đăng ký, user tự tạo nhóm hoặc tham gia nhóm.
  - **Function `dashboard_view()`**: Dashboard hiển thị các nhóm mà người dùng đang tham gia.
- **File: `apps.py`**
  - **Class `CoreConfig`**: Chưa có mô tả Class
- **File: `admin.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `urls.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `context_processors.py`**
  - **Function `company_list()`**: Hàm chức năng
- **File: `decorators.py`**
  - **Function `profile_required()`**: Hàm chức năng
- **File: `forms_profile_customer.py`**
  > *Mô tả:* Định nghĩa các Form cho việc thiết lập thông tin người dùng và công ty.
  - **Class `ProfileSetupForm`**: Form dùng để người dùng thiết lập công ty hoặc tham gia công ty trong lần đầu đăng nhập.
    - *Method `clean_tax_code()`*: Kiểm tra mã số thuế có hợp lệ hay đã tồn tại chưa.
    - *Method `save()`*: Logic lưu dữ liệu: Tạo Company mới (nếu chưa có) và gắn vào Profile của User.
- **File: `forms_register.py`**
  - **Class `RegistrationForm`**: Chưa có mô tả Class
- **File: `tests.py`**
  - **Function `test_user_has_profile_property()`**: Hàm chức năng
- **File: `views_dev copy.py`**
  - **Function `get_manifest_content()`**: Hàm chức năng
  - **Function `architecture_dashboard()`**: Hàm chức năng
  - **Function `download_manifest()`**: Hàm chức năng
- **File: `views_dev.py`**
  - **Function `get_manifest_content()`**: Hàm chức năng
  - **Function `architecture_dashboard()`**: Hàm chức năng
  - **Function `download_manifest()`**: Hàm chức năng
- **File: `__init__.py`**
  - *(File trống hoặc không chứa Class/Function)*

### App: `group_chat`
> *Mô tả:* Quản lý Nhóm, Thành viên, Tài liệu, Vòng đời tri thức và Feedback.

#### 📂 Cấu trúc thư mục & tệp tin:
  ├── 📄 `__init__.py`
  ├── 📄 `admin.py`
  ├── 📄 `apps.py`
  ├── 📄 `consumers.py`
  ├── 📁 **management/**
  │   └── 📁 **commands/**
  │       └── 📄 `init_dev_data.py`
  ├── 📄 `models.py`
  ├── 📄 `routing.py`
  ├── 📁 **services/**
  │   └── 📄 `feedback_service.py`
  ├── 📄 `signals.py`
  ├── 📄 `tests.py`
  ├── 📄 `urls.py`
  └── 📄 `views.py`

#### 🔍 Phân tích chi tiết mã nguồn (AST):
- **File: `models.py`**
  > *Mô tả:* Mục đích: Định nghĩa các thực thể cốt lõi cho Nhóm làm việc và Vòng đời tri thức.
  - **Class `ChatGroup`**: Đại diện cho một nhóm làm việc độc lập. 
    - *Method `__str__()`*: Hàm xử lý nội bộ
  - **Class `Membership`**: Quản lý thành viên trong nhóm.
    - *Method `__str__()`*: Hàm xử lý nội bộ
  - **Class `Document`**: Lưu trữ file gốc để trích xuất tri thức.
  - **Class `KnowledgeUnit`**: Đơn vị kiến thức (RAG Source).
  - **Class `Message`**: Tin nhắn trong nhóm.
  - **Class `MessageFeedback`**: Feedback loop để tinh chỉnh AI (Fine-tuning Data).
- **File: `signals.py`**
  > *Mô tả:* Mục đích: Tự động hóa các tác vụ ngầm thông qua Django Signals.
  - **Function `create_ai_member()`**: Khi nhóm mới được tạo, tự động gán AI làm thành viên.
  - **Function `process_document_knowledge()`**: Khi có file mới, tạo KnowledgeUnit và kích hoạt xử lý bất đồng bộ.
  - **Function `cleanup_vector_store_on_doc_delete()`**: Khi xóa tài liệu, xóa tất cả KnowledgeUnit và embedding liên quan.
  - **Function `sync_knowledge_to_vector_db()`**: Đồng bộ dữ liệu vào Vector DB dựa trên trạng thái duyệt.
- **File: `views.py`**
  > *Mô tả:* Mục đích: Xử lý logic nghiệp vụ cho nhóm chat, quản lý tài liệu và tri thức.
  - **Function `create_group()`**: Tạo nhóm mới. Mọi nhóm là một Tenant độc lập.
  - **Function `upload_document()`**: Upload tài liệu vào nhóm.
  - **Function `knowledge_management()`**: Dashboard cho Admin nhóm để duyệt hoặc rollback tri thức.
  - **Function `rollback_knowledge()`**: Hành động Rollback: Chuyển trạng thái KnowledgeUnit -> Xóa khỏi VectorDB.
  - **Function `group_chat_detail()`**: Hiển thị giao diện chat chính của nhóm.
  - **Function `knowledge_feedback_view()`**: Hàm chức năng
- **File: `apps.py`**
  > *Mô tả:* Mục đích: Cấu hình App group_chat và đăng ký Signals.
  - **Class `GroupChatConfig`**: Chưa có mô tả Class
    - *Method `ready()`*: Phương thức này chạy khi dự án khởi động.
- **File: `admin.py`**
  - **Class `ChatGroupAdmin`**: Chưa có mô tả Class
  - **Class `DocumentAdmin`**: Chưa có mô tả Class
  - **Class `KnowledgeUnitAdmin`**: Chưa có mô tả Class
- **File: `urls.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `consumers.py`**
  > *Mô tả:* File: apps/group_chat/consumers.py
  - **Class `ChatConsumer`**: Chưa có mô tả Class
    - *Method `save_message()`*: Hàm xử lý nội bộ
- **File: `routing.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `tests.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `__init__.py`**
  - *(File trống hoặc không chứa Class/Function)*

### App: `subscriptions`
> *Mô tả:* Quản lý gói dịch vụ và giới hạn thành viên theo ChatGroup.

#### 📂 Cấu trúc thư mục & tệp tin:
  ├── 📄 `__init__.py`
  ├── 📄 `admin.py`
  ├── 📄 `apps.py`
  ├── 📄 `models.py`
  ├── 📄 `signals.py`
  ├── 📄 `tests.py`
  ├── 📄 `urls.py`
  └── 📄 `views.py`

#### 🔍 Phân tích chi tiết mã nguồn (AST):
- **File: `models.py`**
  > *Mô tả:* Mục đích: Quản lý gói cước và giới hạn thành viên cho từng ChatGroup.
  - **Class `Subscription`**: Quản lý trạng thái và giới hạn của nhóm.
    - *Method `__str__()`*: Hàm xử lý nội bộ
- **File: `signals.py`**
  > *Mô tả:* Mục đích: Tự động khởi tạo gói dịch vụ cho nhóm mới.
  - **Function `create_default_subscription()`**: Khi ChatGroup mới được tạo, tự động tạo gói 'free' cho nhóm đó.
- **File: `views.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `apps.py`**
  - **Class `SubscriptionsConfig`**: Chưa có mô tả Class
    - *Method `ready()`*: Hàm xử lý nội bộ
- **File: `admin.py`**
  - **Class `SubscriptionAdmin`**: Chưa có mô tả Class
- **File: `urls.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `tests.py`**
  - *(File trống hoặc không chứa Class/Function)*
- **File: `__init__.py`**
  - *(File trống hoặc không chứa Class/Function)*