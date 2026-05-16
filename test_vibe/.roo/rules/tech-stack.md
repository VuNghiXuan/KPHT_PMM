# 💻 TIÊU CHUẨN KỸ THUẬT (TECH-STACK)

## 🐍 BACKEND ARCHITECTURE
- **Framework:** Django 5.x.
- **Database:** - PostgreSQL/MySQL cho dữ liệu giao dịch và metadata.
    - **Neo4j:** Dành cho GraphRAG và mối quan hệ tri thức nghiệp vụ.
- **Environment:** Sử dụng Virtual Environment, cài đặt qua `pip`.

## 🤖 AI & DATA PROCESSING
- **Model:** Chạy Local qua **Ollama** (Ưu tiên `qwen2.5-coder:7b` cho code và `qwen2.5:7b` cho bối cảnh).
- **Excel Processing:** Sử dụng `pandas`, `openpyxl`. Chú trọng việc xử lý Merge Cells và Table Regions trong 300 sheet của KPHT.
- **RAG Flow:** - Embedding dữ liệu từ Excel Miner.
    - Lưu vào Vector Database hoặc Neo4j.
    - Sử dụng LangChain/LangGraph để điều phối Agent.

## 📁 CẤU TRÚC MODULE (FOLDER STRUCTURE)
- `apps.app_miner`: Chịu trách nhiệm quét và bóc tách "quặng" từ file Excel.
- `apps.app_knowledge`: Quản lý kho tri thức, GraphRAG và Neo4j.
- `apps.app_coach`: Giao diện duyệt tri thức, xử lý câu hỏi Uncertainty từ AI.
- `apps.app_ai_core`: Gateway kết nối Ollama/Groq và quản lý Prompt Config.

## 🧪 TESTING & QUALITY
- Luôn chạy kiểm thử sau khi sửa logic bóc tách Excel.
- Ưu tiên viết code dạng Module, dễ tái sử dụng (DRY Principle).