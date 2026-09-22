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

-----
📊 BÁO CÁO TỔNG HỢP TRẠNG THÁI HỆ THỐNG VNXCHATBOTI. NHỮNG NỘI DUNG ĐÃ XỬ LÝ XONG (DONE - BỎ QUA) 🟢Các hạng mục dưới đây đã được phát triển, kiểm thử và xác nhận hoạt động ổn định, tuân thủ đúng nguyên tắc Group-Centric (Không rò rỉ dữ liệu giữa các nhóm) và Modular Monolith:1. Hạ tầng Nền tảng & Cấu hình AI Gateway✅ Môi trường & Kết nối: Kết nối ổn định Redis (Caching/WebSocket Layer), Groq API Key, chuẩn hóa LLM mặc định sang qwen/qwen3.8-27b thông qua DefaultConfig. Tự động fallback chạy CPU khi không có CUDA.✅ Kiểm soát Lỗi 429 (Rate Limit): Đã kiểm tra và chẩn đoán qua các log thực tế (test_flow và test suites). Luồng Celery Worker và AI Engine không còn gặp ngoại lệ 429 Too Many Requests.✅ Phân hệ Core & Subscriptions: Quản lý User/Profile kèm signals.py tự động khởi tạo Profile & ChatGroup riêng. Tự động cấp gói cước Free cho nhóm mới.✅ Nội soi Hệ thống (arch_manager): Đã hoàn thiện Engine quét mã nguồn tự động xuất biểu đồ Mermaid (ERD, Code Flow, Component) và cập nhật VNX_PROJECT_MANIFEST.md.2. Luồng Xử lý Tri thức & Vector Store (Core Logic)✅ Quy tắc Vàng Vector Store: Tín hiệu signals.py chặn triệt để dữ liệu ở trạng thái pending, staging, conflict_detected không cho nạp vào ChromaDB. Chỉ đồng bộ khi chuyển sang approved.✅ Hard Scoping Vector Store: Mọi truy vấn VectorDBManager đều bắt buộc lọc theo metadata={"group_id": current_group_id}.✅ Cơ chế Tự phục hồi AI Engine: Khi LLM trả về phản hồi không thể json.loads() trực tiếp (do dính Markdown code block), cơ chế Fallback trích xuất thô đã tự xử lý thành công không làm gián đoạn chương trình.II. NHỮNG NỘI DUNG CẦN THỰC HIỆN TIẾP (TODO - CÔNG VIỆC CHO NGÀY MAI) 🔴Dựa trên các thiếu hụt (Gap Analysis) và định hướng nâng cấp 1% hiệu năng, dưới đây là 3 nhóm nhiệm vụ trọng tâm:[MỤC TIÊU NGÀY MAI]
 ├── 1. Tối ưu AI Engine & Chuỗi Task Celery (Backend)
 ├── 2. Kết nối Pipeline Chống trùng lặp & Mâu thuẫn Tri thức (AI Power)
 └── 3. Hoàn thiện Giao diện Quản trị Vòng đời Tri thức (Frontend UI/UX)
🟢 NHÓM 1: Tối ưu Backend & Khắc phục Cảnh báo (Low-level Optimization)1.1 Tối ưu hóa Parser JSON trong AI_EngineHiện trạng: Logs cảnh báo ⚠️ [AI_Engine] Không thể parse JSON trực tiếp....Cần làm: Bổ sung hàm tiền xử lý clean_json_markdown() trong AI_Engine để tự động loại bỏ các thẻ ```json ... ``` trước khi parse. Giúp loại bỏ hoàn toàn cảnh báo này trong log.1.2 Khắc phục Cảnh báo Đồng bộ VectorDB trong Unit TestHiện trạng: Unit test báo ⚠️ [Signals] Đồng bộ VectorDB không thành công... do test case sử dụng Dummy/Mock UUID chưa khởi tạo Collection thực tế.Cần làm: Cập nhật fixture/mocking trong apps/ai_assistant/tests/ để giả lập ChromaDB Collection chuẩn xác khi test signal post_save.1.3 Nâng cấp Chunking & Điều phối Celery TaskCần làm:Tích hợp kỹ thuật Token Budgeting & Semantic Chunking vào DocumentProcessorService (gom nhóm đoạn nhỏ, cắt nhỏ đoạn lớn theo ranh giới tự nhiên).Cấu hình bổ sung exponential_backoff và rate_limit trong apps/ai_assistant/tasks.py để đề phòng quá tải khi nạp file lớn trong tương lai.🟡 NHÓM 2: Hoàn thiện Vòng đời Tri thức & Xử lý Mâu thuẫn (Knowledge Lifecycle)2.1 Chuẩn hóa Luồng P1 & P2 Background PipelineCần làm: Rà soát và kết nối liền mạch chuỗi tác vụ:$$\text{Upload File} \xrightarrow{\text{STAGING}} \text{process\_document\_task} \xrightarrow{\text{PENDING}} \text{detect\_semantic\_overlap\_task} \xrightarrow{\text{Sim} \ge 0.85} \text{ConflictService}$$2.2 Rà soát Cơ chế Phát hiện Trùng lặp (ConflictService)Cần làm: Đảm bảo khi Cosine Similarity $\ge 0.85$, hệ thống tự động gán nhãn conflict_detected và lưu cấu trúc gợi ý biên soạn ai_rewrite_suggestion vào cơ sở dữ liệu.🔵 NHÓM 3: Hoàn thiện Giao diện Quản trị & Human-in-the-Loop (Frontend UI/UX)3.1 Cập nhật Models & DB Schema (nếu chưa đồng bộ)Cần làm: Kiểm tra và bổ sung các trường: ConfidenceScore, Status (Enum: PENDING, STAGING, APPROVED), HasConflict, và raw_structure_json vào model Document/KnowledgeChapter.3.2 Nâng cấp Bảng Dashboard Tri thức (knowledge_dashboard.html & document_list.html)Cần làm:Bổ sung cột Meta-data tệp (Dung lượng, Định dạng, Thời gian tải lên).Thêm Badge trực quan hiển thị Trạng thái (Pending, Staging, Approved) và Cảnh báo mâu thuẫn (Has Conflict).Thêm thanh Search tri thức toàn cục theo nhóm ngay trên Dashboard.3.3 Tích hợp Modal "Nhờ AI Biên Soạn" & Realtime Progress BarCần làm:Thêm Textarea nhận prompt chỉnh sửa của Admin trong Modal chi tiết chương.Kết nối JS handleAIRewrite() gọi API /api/knowledge/rewrite/.Thêm JS Polling/WebSocket cập nhật Tiến độ xử lý (Progress Bar) khi Celery Task đang chạy.🎯 KẾ HOẠCH BẮT ĐẦU CHO NGÀY MAISáng mai khi bắt đầu, chúng ta sẽ thực hiện theo thứ tự ưu tiên từng bước (Step-by-Step Protocol):Bước 1: Xử lý triệt để lớp AI_Engine (loại bỏ cảnh báo JSON parse) và chỉnh sửa mock test cho signals.py.Bước 2: Cập nhật DocumentProcessorService (Semantic Chunking & Token Budgeting).Bước 3: Cập nhật UI (knowledge_dashboard.html, document_list.html) để hiển thị đúng Badge Trạng thái và Mâu thuẫn.

---
📊 1. Tóm tắt những phần đã HOÀN THÀNHChúng ta đã hoàn thiện thành công nền tảng backend của hệ thống VnxChatBot theo đúng các nguyên tắc kiến trúc:🏢 Cô lập dữ liệu theo Nhóm (Group-Centric Tenant Isolation): Tất cả từ Vector DB (ChromaDB), Redis Semantic Cache, cho đến các truy vấn dữ liệu đều đã được thiết lập bộ lọc theo group_id.📜 Vòng đời Tri thức & Quy tắc Vàng (Knowledge Lifecycle):Luồng bóc tách tài liệu từ trạng thái staging $\rightarrow$ tạo KnowledgeChapter nháp (pending).Phát hiện trùng lặp ngữ cảnh (detect_semantic_overlap_task) với ngưỡng Cosine Similarity $\ge 0.85$.Thực hiện Quy tắc Vàng: Dữ liệu pending/staging hoàn toàn không bị rò rỉ vào Vector DB; chỉ khi quản trị viên phê duyệt (approved), tín hiệu signals.py mới kích hoạt đẩy vector vào ChromaDB.⚡ Hiệu năng & Bất đồng bộ (Async & Caching):Tích hợp Celery + Redis để xử lý các tác vụ nặng (embedding, chunking, kiểm tra trùng lặp).Redis Semantic Cache hoạt động mượt mà cho luồng truy vấn RAG.🛡️ Hệ thống Kiểm thử (Unit Tests & Diagnostics): Pass toàn bộ các suite test thuộc core, group_chat, ai_assistant, subscriptions, arch_manager và kịch bản chẩn đoán test_flow.🚀 2. Các bước TIẾP THEO nên làmBây giờ hệ thống lõi đã vững chắc, chúng ta có thể chuyển sang giai đoạn vận hành & kết nối thực tế:Chuyển đổi cấu hình Embedding thực tế (Tối ưu Waring LiteLLM):Trong .env, bạn đã có GOOGLE_API_KEY. Chúng ta có thể chuyển mô hình Embedding mặc định sang Gemini (text-embedding-004) để vừa sử dụng API thực vừa xóa sạch các thông báo warning của LiteLLM.Kiểm thử giao diện WebSocket Realtime (ChatConsumer):Tiến hành chạy server thực tế (python manage.py runserver) và mở giao diện Web/Chat Client để test gửi tin nhắn hỏi-đáp RAG thực tế trong nhóm.Hoàn thiện API Phê duyệt Tri thức (Knowledge Approval UI/API):Kiểm tra giao diện người dùng (hoặc API Endpoint) dành cho Admin nhóm để thực hiện thao tác xem các đoạn tri thức bị trùng lặp, duyệt (approved), hoặc dùng tính năng gợi ý viết lại (ai_rewrite_suggestion).