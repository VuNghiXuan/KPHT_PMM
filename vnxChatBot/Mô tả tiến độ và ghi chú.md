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
📊 Tổng kết tiến độ hệ thống
✅ Những việc đã hoàn thành
🛠️ Sửa lỗi lệch Data Model:

Điều chỉnh chuẩn xác các tham số khởi tạo trong KnowledgeUnit (entity_name).

Khớp hoàn toàn các thuộc tính trong DocumentProcessorService với Model KnowledgeChapter thực tế (title, summary, suggested_content, has_conflict, status).

📄 Trích xuất & Chunking tài liệu (Phase 1):

Thư viện Docling + RapidOCR trích xuất file PDF (QTrinh_MuaBanDoi_de.pdf) sang Markdown cực kỳ trôi chảy (~15–19 giây).

Thuật toán Semantic Chunking phân rã nội dung thô thành 14 chương nháp (chunks) an toàn dựa trên Token Budget.

🚀 Celery Task thành công 100%:

Celery Worker thực thi task process_document_task thành công, lưu 14 bản ghi KnowledgeChapter (trạng thái PENDING) vào CSDL mà không phát sinh lỗi.

⏳ Những việc cần làm tiếp (Buổi sau làm tiếp)
🎨 Sửa lỗi Hiển thị UI & Parser dữ liệu (Mới bổ sung):

Sửa lỗi chữ bị xén/vỡ nét: Điều chỉnh CSS (line-height, overflow: hidden) ở tiêu đề chi tiết chương góc trên bên phải.

Render bảng Markdown: Chuyển đổi dữ liệu bảng thô dạng | Bước | TL |... sang giao diện bảng HTML chuẩn để người dùng dễ quan sát.

Làm sạch tiêu đề chương: Tối ưu bộ Parser để lọc bỏ các ký tự Markdown thừa dính trong tiêu đề (ví dụ: ## GIAI ĐOẠN 2...).

🧠 Tối ưu Ngữ cảnh Chunking cho AI Chat (Mới bổ sung):

Khắc phục tình trạng đứt gãy ngữ cảnh giữa các bước quy trình nối tiếp nhau (Phần 7, 8, 9, 10...).

Giải pháp: Cấu hình Overlap (đoạn gối đầu) hoặc bổ sung Metadata/Tiêu đề cha vào từng chunk để AI không bị mất thông tin khi truy vấn (RAG).

🔍 Kiểm tra View & Hiển thị Cây Mục lục:

Kiểm tra QuerySet trong View của route /groups/<id>/knowledge/ xem vì sao 14 chương đã có trong CSDL nhưng chưa đổ ra bảng "Cây Mục lục Tri thức".

Cập nhật trạng thái giao diện của RawDocument từ PENDING sang STAGING / PROCESSED sau khi Celery hoàn thành.

🟢 Thử nghiệm Luồng Phê duyệt (Approve) & Embed Vector DB:

Thực hiện thao tác Phê duyệt chương trên giao diện (Human-in-the-Loop).

Kiểm tra xem Signal/Task commit_to_vector_db có tự động đẩy các vector embedding vào Vector Store (ChromaDB/FAISS) hay không.

🤖 Kiểm tra AI Auditor (Phát hiện xung đột):

Chạy và kiểm tra task detect_semantic_overlap_task để phát hiện mâu thuẫn ngữ nghĩa giữa các chương mới và tri thức cũ.


----Ngày 16.10.2026------------
⏳ Những việc cần làm tiếp
🎨 Sửa lỗi Hiển thị UI & Parser dữ liệu:

📐 Sửa lỗi CSS: Điều chỉnh line-height và overflow ở tiêu đề chi tiết chương góc trên bên phải để tránh bị xén/vỡ nét.

📊 Render Bảng: Chuyển đổi dữ liệu bảng Markdown thô sang giao diện bảng HTML chuẩn.

🧹 Bộ Parser & Làm sạch Tiêu đề (Mô hình Lai 2 Lớp):

Lớp 1 (Regex - Ưu tiên Local ⚡): Sửa lỗi thưa chữ do OCR (Ki ểm k ê ➔ Kiểm kê), xóa ký tự thừa (##, ·, -). Nếu dòng đầu là tiêu đề chuẩn, lấy ngay làm title.

Lớp 2 (LLM Fallback 🤖): Nếu Lớp 1 phát hiện tiêu đề không có ý nghĩa (chứa công thức toán, ngày tháng...), gọi model nhẹ tóm tắt tự động đặt tiêu đề ngắn (3–5 từ).

🧠 Tối ưu Ngữ cảnh Chunking cho AI Chat:

🧱 Option 1 (Small-to-Big): Cắt chunk nhỏ để tìm kiếm chính xác, trả về nguyên KnowledgeChapter lớn cho LLM.

🏷️ Option 2 (Contextual Retrieval): Dùng model nhẹ sinh ngữ cảnh ngắn đính kèm vào từng chunk trước khi lưu Vector DB.

🕸️ Option 3 (Linked Chunking): Thêm trường prev_chapter_id / next_chapter_id vào CSDL để kéo theo các bước quy trình liền kề.

🔍 Kiểm tra View & Hiển thị Cây Mục lục:

🌳 Debug QuerySet trong View /groups/<id>/knowledge/ để hiển thị 14 chương lên Cây Mục lục.

🔄 Cập nhật trạng thái RawDocument từ PENDING sang PROCESSED.

🟢 Thử nghiệm Luồng Phê duyệt (Approve) & Embed Vector DB:

👤 Thực hiện phê duyệt chương trên giao diện (Human-in-the-Loop).

⚡ Kiểm tra Task commit_to_vector_db tự động đẩy embedding vào Vector Store (ChromaDB/FAISS).

🤖 Kiểm tra AI Auditor:

⚔️ Chạy task detect_semantic_overlap_task phát hiện mâu thuẫn ngữ nghĩa.


📂 Các file code cần làm việc (Bạn chuẩn bị/mở sẵn các file này)
Để triển khai bộ Parser Lai 2 Lớp (Regex + LLM) và làm sạch dữ liệu, chúng ta sẽ làm việc với các file sau:

services/document_processor_service.py (hoặc nơi định nghĩa hàm xử lý chunking/extract text):

Nhiệm vụ: Thêm hàm Regex sửa lỗi OCR (Ki ểm k ê ➔ Kiểm kê), làm sạch ##, và kiểm tra tiêu đề hợp lệ.

tasks/document_tasks.py (nơi chứa Celery Task process_document_task):

Nhiệm vụ: Tích hợp logic Lớp 2 (LLM Fallback) để tự động gọi AI đặt tiêu đề khi Regex Lớp 1 thất bại (tiêu đề chứa bảng/công thức).

templates/... hoặc File CSS/JS Frontend (Làm ở bước UI tiếp theo):

Nhiệm vụ: Thêm class CSS chỉnh line-height, overflow và thư viện render bảng HTML từ Markdown (như marked.js hoặc markdown-it).
-------------------------
16.10.2023 (Phần nay chưa xong nha)

🟢 Các mục đã hoàn thành (Done)🧹 Bộ Parser Lai 2 Lớp (Regex + LLM Fallback):Hàm Regex làm sạch chữ bị thưa do lỗi OCR (Ki ểm k ê ➔ Kiểm kê), loại bỏ ký tự thừa (##, ·) trong document_processor_service.py.Tích hợp LLM Fallback trong Celery task process_document_task (tasks/document_tasks.py) để tự động đặt tiêu đề khi Regex thất bại.🎨 Giao diện & CSS Base:Bố cục Master-Detail và khung Danh sách chương.Cấu hình CSS (line-height, overflow) cho phần hiển thị tiêu đề chi tiết chương góc trên bên phải.
⏳ Các việc còn lại cần triển khai tiếpHạng mụcChi tiếtTệp / Thành phần liên quan1. Render Bảng Markdown 📊Chuyển đổi dữ liệu bảng Markdown thô sang bảng HTML chuẩn trên giao diện.Thư viện marked.js hoặc custom parser frontend2. Tối ưu Chunking & Vector DB 🧠Lựa chọn & kiểm thử chiến lược Chunking (Option 1: Small-to-Big, Option 2: Contextual Retrieval, Option 3: Linked Chunking).tasks/document_tasks.py & Vector Store (ChromaDB/FAISS)3. Cây Mục lục & Trạng thái 🔍Debug QuerySet để hiển thị đủ 14 chương lên Cây Mục lục và chuyển trạng thái RawDocument từ PENDING ➔ PROCESSED.Views & DB Query4. AI Auditor & Phê duyệt 🤖Thử nghiệm luồng Phê duyệt thủ công và chạy task detect_semantic_overlap_task kiểm tra mâu thuẫn ngữ nghĩa.


----21.10.2026---
📊 THỐNG KÊ TIẾN ĐỘ DỰ ÁN🟢 1. CÁC HẠNG MỤC ĐÃ HOÀN THÀNH (P1 & P2 + Testing)🛠️ Dịch vụ Bóc tách & Làm sạch (TextCleanerService):📝 Layout-Aware Chunking & Table Formatter (|| $\rightarrow$ \n|) giúp giữ nguyên cấu trúc bảng Markdown.🏷️ Context Scope Injection: Tự động chèn thẻ phân hệ nghiệp vụ vào tiêu đề chunk.🔍 Regex Escape Parser: Bóc tách chính xác [TITLE] và [SUMMARY], chống tràn chuỗi.⚡ Task P1 - Background Processing (process_document_task):📑 Đọc RawDocument (STAGING) và tạo các bản ghi KnowledgeChapter nháp (pending).🗂️ Tách biệt Metadata (summary) và Raw Content đầy đủ (suggested_content).🧠 Task P2 - Kiểm tra trùng lặp Ngữ nghĩa (detect_semantic_overlap_task):🎯 Embedding & Hard Scoping: Truy vấn Vector Store bắt buộc có bộ lọc group_id.⚖️ Xử lý xung đột (Cosine $\ge 0.85$): Chuyển trạng thái conflict_detected và gọi ConflictService bằng Local Ollama để tạo gợi ý hợp nhất.🖥️ Giao diện & Kiểm thử (Frontend & Unit Tests):🎨 Master-Detail Dashboard: Khắc phục hiển thị suggested_content trên template HTML.✅ Test Suites: 100% bộ test (apps.core, apps.group_chat, apps.ai_assistant, apps.subscriptions, apps.arch_manager) đã chạy qua (OK).⏳ 2. CÁC HẠNG MỤC CHƯA HOÀN THÀNH / CẦN TRIỂN KHAI TIẾP (P3 & P4)🛡️ Giai đoạn P3 - Rào chắn "Quy tắc Vàng" Vector Store (signals.py):🔴 Chưa rà soát trực tiếp mã nguồn signals.py: Cần kiểm tra rào chắn logic để đảm bảo dữ liệu ở các trạng thái pending, staging, conflict_detected, rejected tuyệt đối không bị lọt vào ChromaDB.🟢 Đồng bộ khi Phê duyệt (APPROVED): Kiểm tra xem hàm sync_chapter_to_vector_async đã nhận tín hiệu post_save chuẩn xác khi người dùng thao tác trên giao diện hay chưa.🚀 Giai đoạn P4 - Nâng cấp Advanced RAG (Lộ trình mở rộng):🔀 Hybrid Search: Kết hợp BM25 (Full-text Search) với Vector Search qua thuật toán Reciprocal Rank Fusion (RRF).📊 Lightweight Reranking: Bổ sung mô hình Cross-Encoder (bge-reranker-base) để xếp hạng lại Top 15–20 kết quả trước khi đưa vào Prompt LLM.⚡ Semantic Caching: Cấu hình Redis Cache để lưu kết quả các câu hỏi có độ tương đồng $> 95\%$, giảm thời gian phản hồi TTFT.Chúng ta nên bắt đầu bằng việc kiểm tra rào chắn P3 hay chuyển sang thiết kế P4?🛡️ Rà soát signals.py (P3): Mở và kiểm tra logic rào chắn dữ liệu chưa duyệt và cơ chế đồng bộ khi bấm Phê duyệt.🔀 Bắt đầu P4 (Advanced RAG): Lập kế hoạch và triển khai Hybrid Search (BM25 + Vector Search + RRF).

---Đang làm---

📜 1. Nhật ký hoàn thành (Completion Log)Nền tảng & Kiến trúc Core (100% Passed Test):Đã cô lập tuyệt đối dữ liệu theo group_id cho mọi truy vấn ORM, ChromaDB Vector Store và Redis Cache.Hoàn thiện mô hình vòng đời tri thức: RawDocument (STAGING) $\rightarrow$ KnowledgeChapter (PENDING / CONFLICT) $\rightarrow$ APPROVED $\rightarrow$ Vector Store.Khắc phục hoàn toàn lỗi trùng lặp Signals và tối ưu đồng bộ bất đồng bộ qua Celery Task (sync_chapter_to_vector_async) với transaction.on_commit.Nâng cấp Pipeline Xử lý Tri thức (Adaptive Knowledge Pipeline):Tích hợp cơ chế Tự động Phân loại Phân hệ bằng Cosine Similarity (classify_text_domain).Chuẩn hóa KnowledgeChapter.metadata phục vụ chính xác tính năng trích dẫn nguồn (RAG Citation).Định hình xong chuẩn thiết kế Pipeline 3 Tầng:Tầng 1 (Layout Reconstruction): Tự động dựng Heading (#, ##) cho file thô/Word/Excel.Tầng 2 (Block-Level Chunking): Cắt đoạn theo khối Điều/Khoản luật, Bảng Markdown kèm tiêm lại Header, và Quy trình SOP.Tầng 3 (Breadcrumb Injection): Tiêm ngữ cảnh cấp cha vào từng Chunk.🎯 2. Kế hoạch bước tiếp theo (Next Action Plan)Bây giờ chúng ta sẽ bắt tay vào Chuyển đổi code thực tế tại apps/ai_assistant/services/document_processor.py và tasks.py theo đúng bộ chỉ dẫn mới:📍 BƯỚC 1: Triển khai Tầng 1 & 2 của Adaptive Pipeline (DocumentProcessorService)Viết hàm nhận diện loại khối (detect_block_type) trong văn bản:Pattern Pháp lý: Regex nhận diện Điều \d+, Khoản \d+, Chương [I-X]+.Pattern Bảng: Nhận diện dòng chứa | và cấu trúc Bảng Markdown.Pattern SOP: Nhận diện Bước \d+ hoặc danh sách số thứ tự.Cập nhật hàm chunking linh hoạt adaptive_block_chunking() thay thế cho việc cắt cố định chunk_by_token_budget().📍 BƯỚC 2: Triển khai Tầng 3 - Tiêm Bối cảnh (Breadcrumb Injector)Xây dựng hàm tạo đường dẫn ngữ cảnh:Ví dụ: [Nguồn: Điều 5 - Quy định Thanh toán] + \n + [Nội dung Chunk]Đảm bảo chuỗi bối cảnh này được đẩy trực tiếp vào KnowledgeChapter.suggested_content và tính toán Embedding.📍 BƯỚC 3: Cập nhật Celery Task & Kiểm thử bổ sung (Unit Test)Cập nhật process_document_task trong apps/ai_assistant/tasks.py chạy qua DocumentProcessorService mới.Viết Unit Test kiểm thử các ca biên:Upload 1 văn bản Luật $\rightarrow$ Kiểm tra xem các Điều có bị cắt đôi hay không.Upload 1 file Bảng định mức dài $\rightarrow$ Kiểm tra các Sub-chunk có được tiêm lại Header cột hay không.

Anh xem kế hoạch triển khai 3 bước này đã tối ưu chưa? Nếu sẵn sàng, chúng ta sẽ bắt đầu ngay với BƯỚC 1: Cập nhật DocumentProcessorService với Adaptive Block Chunking!