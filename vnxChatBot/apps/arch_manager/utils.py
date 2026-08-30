"""
Module: arch_manager.utils
Author: Kỹ sư Phần mềm Cao cấp / Kiến trúc trưởng VnxChatBot
Description: Engine nội soi mã nguồn (Living Documentation Engine), 
             cung cấp các phương thức sinh sơ đồ Mermaid trực quan theo chuẩn Group-Centric.
             Tích hợp cơ chế Debug Log chi tiết để kiểm soát luồng dữ liệu thời gian thực 
             cùng hệ sinh thái mở (Marker, Docling, LangGraph, LiteLLM, Neo4j, n8n).
"""
import textwrap
import logging

# Thiết lập logger cho module arch_manager
logger = logging.getLogger(__name__)

class ArchitectureIntrospectionEngine:
    """
    Class: ArchitectureIntrospectionEngine
    Description: 
        Chịu trách nhiệm quét và chuyển đổi cấu trúc ứng dụng, mô hình dữ liệu 
        và luồng nghiệp vụ của VnxChatBot thành cú pháp sơ đồ Mermaid tiêu chuẩn.
    """

    @staticmethod
    def _clean_mermaid(diagram_str: str) -> str:
        """Loại bỏ khoảng trắng thừa toàn cục và ký tự ẩn (non-breaking spaces)."""
        if not isinstance(diagram_str, str):
            logger.error("Đầu vào không phải là chuỗi.")
            return ""
        return textwrap.dedent(diagram_str.replace('\u00a0', ' ')).strip()

    @staticmethod
    def generate_erd() -> str:
        """
        Sinh sơ đồ ERD (Entity Relationship Diagram) tập trung xoay quanh ChatGroup (Group-Centric).
        Gọi phương thức nội soi động từ SystemBlueprint model đồng thời in log kiểm tra.
        """
        try:
            from .models import SystemBlueprint
            erd_content = SystemBlueprint.generate_dynamic_erd()
            if erd_content and len(erd_content.strip()) > 15:
                return erd_content
        except Exception as e:
            logger.warning(f"❌ [DEBUG ERD ERROR]: Không thể quét dynamic erd từ models: {str(e)}")

        fallback_erd = """
        erDiagram
            ChatGroup ||--o{ Membership : contains
            ChatGroup ||--o{ Document : stores
            ChatGroup ||--o{ GroupAIProvider : configures
            Document ||--o{ KnowledgeUnit : extracts
            ChatGroup ||--o{ Subscription : has
        """
        return ArchitectureIntrospectionEngine._clean_mermaid(fallback_erd)
    
    @staticmethod
    def generate_code_flow() -> str:
        """
        Sinh sơ đồ luồng dữ liệu (Code Flow) từ Upload đến LLM RAG Pipeline, 
        tích hợp các thư viện giảm tải code (Marker/Docling, LangGraph, LiteLLM).
        """
        code_flow = """
        sequenceDiagram
            autonumber
            actor User
            participant n8n as n8n Webhook (Optional)
            participant FP as FileProcessor (Marker/Docling)
            participant VS as ChromaDB / Neo4j (GraphRAG)
            participant Router as Multi-Model Router (LiteLLM)
            participant LG as LangGraph (MoA / State Machine)

            Note over User, LG: Luồng Ingestion & Tri thức
            alt Upload trực tiếp hoặc qua n8n
                User->>FP: Upload File / Tài liệu nhóm (group_id)
                n8n->>FP: Đồng bộ dữ liệu tự động từ POS/Drive
            end
            FP->>FP: Bóc tách PDF/Bảng biểu sang Markdown
            FP->>VS: Lưu Embeddings (ChromaDB) & Quan hệ (Neo4j)

            Note over User, LG: Luồng Truy vấn & Phản hồi (RAG & Multi-Agent)
            User->>Router: Gửi câu hỏi qua WebSocket (ChatConsumer)
            Router->>VS: Kiểm tra Semantic Cache (cosine > 0.92)
            alt Cache Miss / Câu hỏi phức tạp
                Router->>LG: Kích hoạt Task Decomposition & MoA Pipeline
                LG->>Router: Tổng hợp dữ liệu phân tầng (Hierarchical Reduce)
            end
            Router->>Router: Kiểm tra Redis Budget & Circuit Breaker (HTTP 429)
            Router-->>User: Trả về kết quả JSON cấu trúc nghiêm ngặt
        """
        return ArchitectureIntrospectionEngine._clean_mermaid(code_flow)

    @staticmethod
    def generate_state_machine() -> str:
        """
        Sinh sơ đồ trạng thái (Knowledge Lifecycle State Machine) bao gồm xử lý mâu thuẫn.
        """
        state_machine = """
        stateDiagram-v2
            [*] --> Pending : Extracted via Docling / Marker (Chapters & Tables)
            Pending --> ConflictDetected : Semantic Overlap >= 0.85
            ConflictDetected --> ReadyToApprove : Admin Conflict Resolution (Update / Merge / Ignore)
            Pending --> ReadyToApprove : Direct Flow (No Conflict)
            ReadyToApprove --> Approved : Admin Final Approval
            Approved --> VectorDB : Auto Index to ChromaDB / Neo4j
            Approved --> Rollback : Delete Embedding via Signals
        """
        return ArchitectureIntrospectionEngine._clean_mermaid(state_machine)
    
    @staticmethod
    def generate_component_diagram() -> str:
        """Sinh sơ đồ kiến trúc phân hệ theo mô hình Modular Monolith."""
        comp_diag = """
        graph TD
            subgraph External_Ecosystem [Hệ sinh thái mở]
                n8n[n8n Workflow] --> CoreSys[apps.core]
                Marker[Marker / Docling] --> AIAssist[apps.ai_assistant]
                Neo4j[(Neo4j DB)] -.-> AIAssist
            end

            subgraph VnxChatBot_Monolith [Kiến trúc Modular Monolith]
                CoreSys[apps.core] --> GroupChat[apps.group_chat]
                GroupChat --> AIAssist[apps.ai_assistant]
                AIAssist --> ArchManager[apps.arch_manager]
            end

            style External_Ecosystem fill:#f9f,stroke:#333,stroke-width:2px
            style VnxChatBot_Monolith fill:#bbf,stroke:#333,stroke-width:2px
        """
        return ArchitectureIntrospectionEngine._clean_mermaid(comp_diag)

    @staticmethod
    def generate_knowledge_pipeline_flow() -> str:
        """Sinh sơ đồ Mermaid biểu diễn chi tiết luồng chia chương, bảng biểu và phê duyệt tri thức."""
        raw_flow = """
        graph TD
            A[User / Admin Upload File] --> B[Document Model Created]
            B --> C[Celery Task: Docling Parser]
            C --> D[Split Document into Chapters & Extract Tables]
            D --> E[AI Audit & Semantic Overlap Check]
            E -->|Overlap >= 0.85| F[KnowledgeChapter: status = conflict_detected]
            E -->|Clean Data| G[KnowledgeChapter: status = pending]
            F --> H[Conflict Resolver UI: Overwrite / Merge / Ignore]
            H --> I[Status: ready_to_approve]
            G --> I
            I -->|Admin Approve| J[KnowledgeUnit.status = approved]
            I -->|Reject / Delete| K[Cleanup Vector Store]
            J --> L[Sync to ChromaDB & Neo4j]
            
            style F fill:#ff9,stroke:#333,stroke-width:2px
            style I fill:#f9f,stroke:#333,stroke-width:2px
            style J fill:#9f9,stroke:#333,stroke-width:2px
            style L fill:#bbf,stroke:#333,stroke-width:2px
        """
        return ArchitectureIntrospectionEngine._clean_mermaid(raw_flow)

    @staticmethod
    def generate_ai_extraction_pipeline() -> str:
        """Tạo sơ đồ luồng (Pipeline) cho quá trình trích xuất dữ liệu AI."""
        raw_pipeline = """
        graph TD
            A[User Uploads File] --> B[Document Created]
            B --> C[Celery Task: Docling Parser]
            C --> D[AI Entity Extraction & Business Tagging]
            D --> E[Confidence Score Evaluation]
            E --> F[Save to Database Model (KnowledgeChapter)]
            
            style A fill:#f9f,stroke:#333,stroke-width:2px
            style C fill:#ccf,stroke:#333,stroke-width:2px
            style F fill:#bfb,stroke:#333,stroke-width:2px
        """
        return ArchitectureIntrospectionEngine._clean_mermaid(raw_pipeline)