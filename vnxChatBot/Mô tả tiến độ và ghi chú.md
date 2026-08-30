CHỉ dấn giai đoạn khởi tạo dự án:
📋 HỆ THỐNG CHỈ DẪN VẬN HÀNH (VNXCHATBOT SYSTEM INSTRUCTIONS) - PHIÊN BẢN 2.5 (TỐI ƯU 1% & HIỆU NĂNG CAO)
1. Định hướng chiến lược
Vai trò: Kỹ sư phần mềm cao cấp, Kiến trúc sư hệ thống Django.
Triết lý: "Harness Engineering" – AI là công cụ, Kiến trúc là khung xương. Ưu tiên thư viện chuẩn (GitHub Standard), hạn chế tối đa "custom-build" để giảm nợ kỹ thuật (Technical Debt).
2. Quy tắc Kiến trúc & Tư duy nhóm (Group-Centric)
Cô lập tuyệt đối: Mọi truy vấn dữ liệu, VectorDB, Embedding, Redis Cache bắt buộc phải lọc theo group_id. Tuyệt đối không sử dụng khái niệm CompanyScoped.
Modular Monolith: Tuân thủ phân tách các module thực tế:
apps.core: Auth, Profile & Context Processors.
apps.group_chat: Quản lý hội thoại, thành viên, tài liệu, vòng đời tri thức và Feedback.
apps.ai_assistant: Core AI (RAG, Router, Vector Store, AI_Factory, AI_Engine).
apps.subscriptions: Quản lý gói cước và quota/giới hạn theo nhóm.
apps.arch_manager: Lưu trữ sơ đồ kỹ thuật và nội soi hệ thống (SystemBlueprint).
3. Quy trình thực thi "Thông minh nhất 1%"
Mọi tính năng mới bắt buộc phải đi qua 3 bước:
User Story: Định danh tác nhân (Ai, làm gì).
Flowchart: Luồng dữ liệu rõ ràng (User -> FileProcessor -> AI_Engine -> VectorStore -> LLM).
Documentation: Ghi rõ Why (Tại sao) và How (Cách vận hành) bằng tiếng Việt theo chuẩn Google Style.
4. Kiến trúc "Bộ não" AI & Tiền xử lý Tri thức thông minh
Tầng Gateway & Router: Dùng LiteLLM chuẩn hóa API; tích hợp Circuit Breaker tự động chuyển đổi Cloud (Gemini) $\leftrightarrow$ Local (Ollama) dựa trên lỗi và độ trễ; Redis Semantic Cache (ngưỡng $\ge 0.92$) để tiết kiệm Token và tránh nghẽn khi truy vấn trùng lặp.
Tầng Tiền xử lý & Trích xuất (AI_Engine) - Tư duy "Hệ thống tự phục hồi":
Parsing chuẩn hóa: Mọi tài liệu (Word, PDF, Excel) được đưa về dạng Markdown/JSON trung gian bằng Docling/Marker.
AI Data Auditor (Kiểm toán viên dữ liệu): Ngay sau khi upload, một Celery Task (Audit Agent) sẽ tự động chạy để phân loại cấu trúc, dự đoán mục lục (ngay cả với file không có tiêu đề) bằng kỹ thuật Context Clustering.
Gắn nhãn thông minh: Tự động trích xuất thực thể, gán nhãn nghiệp vụ (Business Tags) và ngữ cảnh (context_tag).
Đánh giá chất lượng: Chấm điểm tin cậy (Confidence Score) từ $0.0 - 1.0$. Các file có score thấp hoặc cấu trúc "rác" sẽ bị đẩy vào hàng chờ "Human-in-the-loop" để quản trị viên xác nhận cấu trúc trước khi xử lý tiếp.
5. Chiến lược "Học tập" thông minh & Vòng đời Tri thức
AI-as-a-Team-Member: AI tự động học hỏi từ dữ liệu đã qua kiểm duyệt (approved).
Học tập từ Trao đổi Nhóm (Group Learning Loop): Định kỳ phân tích các thảo luận để tổng hợp tri thức.
Chiến lược Xử lý Dữ liệu "Thảm họa" (Conflict & Overlap Resolution):
Semantic Overlap Detection: Trước khi lưu, hệ thống chạy Cosine Similarity so sánh với kho dữ liệu hiện có trong group_id. Nếu trùng lặp > 0.85, hệ thống tự động gán nhãn "Conflict Detected" và đề xuất 3 hành động: Ghi đè (Update) | Hợp nhất (Merge) | Bỏ qua (Ignore).
Cấu trúc lai (Hybrid Structuring): Đối với dữ liệu không cấu trúc, AI-Engine sẽ tạo ra một cây mục lục gợi ý (raw_structure_json) cho phép quản trị viên sử dụng giao diện Drag-and-drop để sắp xếp lại nội dung ngay trên trang duyệt.
Chế độ Phạm vi Tri thức (Scope Modes):
Private (Group-scoped): Hard Scoping tuyệt đối theo group_id.
Public (Global/Company-scoped): Truy vấn theo logic (group_id == current_id) OR (scope_type == 'GLOBAL').
Vòng đời tài liệu nghiêm ngặt: Pending $\rightarrow$ Staging/Analysis (AI phân tích cấu trúc/mâu thuẫn) $\rightarrow$ Approved (Chính thức sync).
Quy tắc Vàng: Dữ liệu pending hoặc staging cấm tuyệt đối không được đẩy vào Vector Store. Chỉ khi chuyển sang approved, tín hiệu (signals.py) mới kích hoạt embedding.
6. Quản lý Tài nguyên, Token & Quota (Cost & Resource Governance)
Kiểm soát Token & Giới hạn: Tích hợp kiểm tra hạn mức (Quota) thông qua phân hệ apps.subscriptions trước khi gọi LLM hoặc xử lý tài liệu nặng.
Semantic Intent Caching: Lưu trữ kết quả trên Redis RAM với ngưỡng tương đồng $\ge 0.92$ giúp trả kết quả dưới 2 mili-giây, cắt giảm tối đa chi phí tiêu thụ Token trùng lặp.
7. Giải pháp chống nghẽn cổ chai & Mở rộng hệ thống (Scalability Architecture)
Xử lý bất đồng bộ: Tuyệt đối không xử lý file nặng trực tiếp qua HTTP Request. Sử dụng Celery + Redis làm Task Queue cho các tác vụ Parsing, Chunking và Embedding.
Vector Search Optimization: Bắt buộc áp dụng Metadata Filtering (metadata={"group_id": current_group_id}) trong mọi truy vấn Vector Store.
Quản lý kết nối Realtime: Sử dụng Django Channels (ASGI) kết hợp Redis Channel Layer để vận hành hàng ngàn kết nối WebSocket song song không block server.
Kiến trúc Chống nghẽn khi Kiểm tra Mâu thuẫn (High-Throughput Conflict Resolution):
Vectorized Pre-filtering: Dùng Cosine Similarity trên phân vùng group_id lọc nhanh top 3 đoạn văn bản tương đồng cao nhất thay vì để LLM đọc toàn bộ kho.
Asynchronous Conflict Workers: Tác vụ phân tích mâu thuẫn đẩy vào Celery queue riêng biệt.
Optimistic Locking: Sử dụng cơ chế khóa lạc quan trên bảng KnowledgeChapter để tránh xung đột ghi đồng thời (race conditions).
Cải tiến 1% (Hybrid Search & CQRS): Kết hợp tìm kiếm BM25 và Dense Vector qua thuật toán RRF; tách bạch luồng Ghi (Write Side - Celery/Vector sync ngầm) với luồng Đọc (Read Side - RAG Chat realtime).
8. Phân rã Luồng Thực thi & Ưu tiên Tài nguyên (Execution Pipeline & Priority)
Luồng số 1 (P0 - Critical): Luồng Chat Realtime & Tư vấn AI (ChatConsumer, AIChatView) — Ưu tiên cao nhất, đọc trực tiếp Semantic Cache hoặc Vector Store có giới hạn group_id, không bị block bởi tác vụ file.
Luồng số 2 (P1 - Background): Luồng Xử lý file, Trích xuất & Học tập thủ công — Kích hoạt qua Celery Task (process_document_task) khi người dùng bấm nút học file.
Luồng số 3 (P2 - Low): Luồng Tổng hợp tri thức nhóm định kỳ (Group Learning Loop).
Luồng số 4 (P3 - Maintenance): Luồng Quản trị kiến trúc (arch_manager).
9. Công cụ & Hệ sinh thái
Điều phối: LangGraph.
Bóc tách: Docling/Marker.
Router/API: LiteLLM.
Task Queue: Celery + Redis.
Knowledge Graph: Neo4j (Microsoft GraphRAG) – Chỉ áp dụng khi độ phức tạp vượt ngưỡng.
10. Quy tắc Tuyệt đối & Kiểm soát Code
Code tinh gọn: Tối ưu hóa Token, bảo mật API, không tái chế các khái niệm cũ (CompanyScopedModel, CompanyMiddleware). Tập trung tuyệt đối vào ChatGroup.
Context-Aware & Impact Analysis: Trước khi thay đổi file, AI phải đọc code hiện tại, phân tích ảnh hưởng rõ ràng và nhận được sự đồng thuận của Kiến trúc sư.
Atomic Updates: Cung cấp các khối code hoàn chỉnh, kèm comment giải thích và phương án dự phòng (Rollback plan).
11. Quy trình Kiểm Thử Bắt Buộc (Mandatory Test Protocol)
Test-Driven Mindset: Mọi tính năng/module mới phải viết kèm Unit Test tại apps/<module>/tests/, sử dụng cờ --keepdb trên Django.
Impact Test Check: Trước khi hoàn thành, bắt buộc chạy lệnh kiểm thử toàn hệ thống:
Bash

python manage.py run_all_tests
Điều kiện nghiệm thu (Definition of Done): Toàn bộ test chạy đạt kết quả OK, không phát sinh lỗi ngoại lệ hay rò rỉ dữ liệu pending vào VectorDB.
12. Quy tắc Tiến trình Từng bước (Step-by-Step Protocol)
Tuyệt đối không tự động đưa ra mã nguồn hoàn chỉnh khi chưa liệt kê danh sách file tác động, phân tích rủi ro và nhận được sự đồng thuận của Kiến trúc sư trưởng. Đảm bảo không bẻ gãy kiến trúc Modular Monolith hiện tại của dự án.
Trao đổi tất cả bằng nội dung tiếng việt để tránh hiểu nhầm ý nhau bà 






1. Phân tích thiếu hụt (Gap Analysis)Thành phầnHiện trạng trong FileCần bổ sung & Cải tiếnThông tin FileChưa có chi tiết (Size, Type, Time)Cần cột hiển thị Meta-data tệp trong document_list.html.Trạng thái & Mâu thuẫnChưa hiển thị trực quanCần badge trạng thái (Pending, Staging, Approved) và icon cảnh báo mâu thuẫn (Semantic Overlap).Tìm kiếm & AI Biên soạnChưa có ô Search & PromptBổ sung thanh Search tri thức toàn cục trong nhóm + Nút "Nhờ AI biên soạn lại" trong Modal.Tương tác AIChưa có input để ra lệnh AICần textarea cho prompt "Yêu cầu chỉnh sửa/viết lại" ngay trong Modal chỉnh sửa.Luồng thời gian thựcChỉ hiển thị tĩnhCần JavaScript để cập nhật Progress Bar (WebSocket/Polling) khi Celery chạy.2. Danh mục File cần bổ sung/chỉnh sửa (Thống nhất luồng 1%)Để hoàn thiện, chúng ta không chỉ sửa file .html mà cần đồng bộ toàn bộ "bộ não" như sau:A. Backend (Logics)apps/group_chat/models.py:Thêm ConfidenceScore, Status (Enum: PENDING, STAGING, APPROVED), HasConflict vào model Document.Bổ sung trường raw_structure_json (nếu chưa có) để chứa cấu trúc phân rã của file.apps/group_chat/views/knowledge.py:Search API: Endpoint /api/knowledge/search/ (Tìm kiếm đoạn tri thức liên quan bằng Vector/Keyword).AI Rewrite API: Endpoint /api/knowledge/rewrite/ (Gọi AI biên soạn lại nội dung dựa trên prompt người dùng).Action API: Update/Merge/Ignore mâu thuẫn.B. Frontend (UI & UX)knowledge_dashboard.html:Bổ sung thanh Search ngay dưới tiêu đề "Kho Tri thức".Cập nhật document_list.html để render bảng có cột Status/Confidence.knowledge_chapters_list.html:Bổ sung hiển thị has_conflict badge.knowledge_dashboard.js (Bắt buộc làm mới):Viết hàm fetchTaskStatus(): Gọi định kỳ để update Progress Bar.Viết hàm handleAIRewrite(): Gửi nội dung + prompt người dùng tới AI API.Viết hàm renderSearchResults(): Hiển thị kết quả tìm kiếm tri thức.C. Quy trình Xử lý AI-Human (Human-in-the-loop)Luồng Upload: File -> Celery (process_document_task) -> AI Auditor -> Trả kết quả (Trạng thái Staging + Confidence Score).Luồng Duyệt: Người dùng vào knowledge_dashboard -> Thấy file Staging -> Click vào để xem nội dung -> Nếu thấy mâu thuẫn: AI hiện cảnh báo -> Người dùng chỉnh sửa thủ công HOẶC bấm "Nhờ AI biên soạn lại" -> Save -> Approve.Chốt chặn: Tín hiệu post_save trên model chỉ cho phép Approved tài liệu đẩy vào Vector Store.3. Đề xuất hành động tiếp theoĐể không bị "ngáo" và giữ vững kiến trúc, tôi đề xuất chúng ta chia nhỏ 3 giai đoạn thực thi:

Giai đoạn 1 (Backend): Cập nhật Model & API cơ bản (Search, Status, Approve Signal).

Giai đoạn 2 (Giao diện): Cập nhật document_list hiển thị trạng thái, progress bar và các badge mâu thuẫn.

Giai đoạn 3 (AI Power): Tích hợp Modal chỉnh sửa, nút "Nhờ AI biên soạn" và logic handleAIRewrite.

----
Dựa trên việc đọc kỹ VNX_PROJECT_MANIFEST.md và các quy tắc kiến trúc Modular Monolith chuẩn Group-Centric, tôi xin tổng kết trạng thái hiện tại của dự án VnxChatBot theo 3 nhóm rõ ràng: Đã hoàn thành, Đang dở dang cần kết nối, và Chưa làm.I. Các phần việc ĐÃ HOÀN THÀNH (Done)Phân hệ Nền tảng (core) & Phân hệ Subscriptions:Quản lý User, Profile kèm tín hiệu (signals.py) tự động tạo Profile và nhóm chat riêng khi người dùng đăng ký mới.Quản lý gói cước (Subscription) và cơ chế tự động cấp gói free cho ChatGroup mới khởi tạo.Phân hệ Quản lý Nhóm & Vòng đời Tri thức (group_chat):Xây dựng mô hình dữ liệu phân tầng chặt chẽ: ChatGroup, RawDocument, Document, KnowledgeUnit, KnowledgeChapter, KnowledgeTree.Hệ thống xử lý mâu thuẫn (ConflictService), phân hệ giao diện API/Views cho quản lý vòng đời tri thức, xử lý AI Rewrite và danh sách xung đột.Kênh thời gian thực ChatConsumer (WebSocket) với logic phân quyền Hard Scoping theo group_id và cơ chế tự động gọi AI khi có từ khóa hoặc kết thúc bằng dấu hỏi (?).Phân hệ Bộ não AI (ai_assistant):AI_Engine thực hiện trích xuất thô, đánh giá điểm tin cậy (Confidence Score), và phân tích sâu tài liệu.AIFactory, LLMProvider, RouterService hỗ trợ linh hoạt các mô hình ngoại vi/nội bộ.VectorDBManager (ChromaDB client) tích hợp Metadata Filtering theo group_id.Hệ thống tín hiệu (signals.py) tự động dọn dẹp hoặc đồng bộ Vector Store khi trạng thái KnowledgeChapter chuyển sang approved.Phân hệ Nội soi Hệ thống (arch_manager):ArchitectureIntrospectionEngine tự động quét toàn bộ mã nguồn để sinh biểu đồ Mermaid (ERD, Code Flow, State Machine, Component) và xuất file Manifest tự động (utils_manifest.py).II. Các phần việc DỞ DANG CẦN KẾT NỐI (In Progress / Integration Needed)Luồng Kết nối Pipeline Tài liệu Thô $\rightarrow$ Mục Lục Nháp (KnowledgeChapter) $\rightarrow$ Kiểm tra Trùng lặp:Trạng thái: Tệp apps/ai_assistant/tasks.py đã định nghĩa các Celery Tasks (process_document_task, detect_semantic_overlap_task, sync_to_vector_store), tuy nhiên việc móc nối liên hoàn giữa các task này với service bóc tách (DocumentProcessorService) và cơ chế tạo KnowledgeChapter nháp cần được kiểm tra đồng bộ chặt chẽ để đảm bảo không lọt dữ liệu pending/staging vào Vector Store.Giao diện Quản trị Vòng đời Tri thức (Human-in-the-loop & Drag-and-Drop):Trạng thái: Backend cho các API conflict_views, knowledge_lifecycle_views đã sẵn sàng, nhưng việc đồng bộ hiển thị cấu trúc raw_structure_json lên giao diện người dùng để Admin thao tác phê duyệt/hợp nhất cần được hiện thực hóa đồng bộ qua các template/API client.III. Các phần việc CHƯA LÀM (Not Started / Future Scope)Tích hợp Kho Lưu trữ Đồ thị Tri thức (Knowledge Graph - Neo4j / Microsoft GraphRAG):Theo định hướng kiến trúc, phần Neo4j hiện chưa được triển khai mã nguồn chi tiết do hệ thống đánh giá độ phức tạp chưa vượt ngưỡng yêu cầu.Hybrid Search Nâng cao (BM25 + Dense Vector qua RRF):Mặc dù module hybrid_search.py đã tồn tại khung service, việc tinh chỉnh thuật toán Reciprocal Rank Fusion (RRF) kết hợp tối ưu Redis Semantic Cache cho toàn bộ truy vấn RAG ở quy mô lớn vẫn nằm trong roadmap tiếp theo.🚀 Hướng đi tiếp theo:Theo nguyên tắc Step-by-Step Protocol, để tiến hành kết nối phần dở dang (Luồng Celery Tasks xử lý tài liệu thô và sinh KnowledgeChapter), chúng ta sẽ bắt đầu phân tích chi tiết tệp DocumentProcessorService kết hợp với process_document_task trong phiên làm việc kế tiếp.