"""
Module: arch_manager.utils
Author: Kỹ sư Phần mềm Cao cấp / Kiến trúc trưởng VnxChatBot
Description: Engine nội soi mã nguồn (Living Documentation Engine), 
             cung cấp các phương thức sinh sơ đồ Mermaid trực quan theo chuẩn Group-Centric.
             Tích hợp cơ chế Debug Log chi tiết để kiểm soát luồng dữ liệu thời gian thực 
             cùng hệ sinh thái mở (Marker, Docling, LangGraph, LiteLLM, Neo4j, n8n).
"""

class ArchitectureIntrospectionEngine:
    """
    Class: ArchitectureIntrospectionEngine
    Description: 
        Chịu trách nhiệm quét và chuyển đổi cấu trúc ứng dụng, mô hình dữ liệu 
        và luồng nghiệp vụ của VnxChatBot thành cú pháp sơ đồ Mermaid tiêu chuẩn.
    """

    @staticmethod
    def generate_erd():
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
            print(f"❌ [DEBUG ERD ERROR]: Không thể quét dynamic ERD từ models: {str(e)}")

        fallback_erd = (
            "erDiagram\n"
            "    ChatGroup ||--o{ Membership : contains\n"
            "    ChatGroup ||--o{ Document : stores\n"
            "    ChatGroup ||--o{ GroupAIProvider : configures\n"
            "    Document ||--o{ KnowledgeUnit : extracts\n"
            "    ChatGroup ||--o{ Subscription : has"
        )
        return fallback_erd
    
    @staticmethod
    def generate_code_flow():
        """
        Sinh sơ đồ luồng dữ liệu (Code Flow) từ Upload đến LLM RAG Pipeline, 
        tích hợp các thư viện giảm tải code (Marker/Docling, LangGraph, LiteLLM).
        """
        code_flow = (
            "sequenceDiagram\n"
            "    autonumber\n"
            "    actor User\n"
            "    participant n8n as n8n Webhook (Optional)\n"
            "    participant FP as FileProcessor (Marker/Docling)\n"
            "    participant VS as ChromaDB / Neo4j (GraphRAG)\n"
            "    participant Router as Multi-Model Router (LiteLLM)\n"
            "    participant LG as LangGraph (MoA / State Machine)\n"
            "\n"
            "    Note over User, LG: Luồng Ingestion & Tri thức\n"
            "    alt Upload trực tiếp hoặc qua n8n\n"
            "        User->>FP: Upload File / Tài liệu nhóm (group_id)\n"
            "        n8n->>FP: Đồng bộ dữ liệu tự động từ POS/Drive\n"
            "    end\n"
            "    FP->>FP: Bóc tách PDF/Bảng biểu sang Markdown\n"
            "    FP->>VS: Lưu Embeddings (ChromaDB) & Quan hệ (Neo4j)\n"
            "\n"
            "    Note over User, LG: Luồng Truy vấn & Phản hồi (RAG & Multi-Agent)\n"
            "    User->>Router: Gửi câu hỏi qua WebSocket (ChatConsumer)\n"
            "    Router->>VS: Kiểm tra Semantic Cache (cosine > 0.92)\n"
            "    alt Cache Miss / Câu hỏi phức tạp\n"
            "        Router->>LG: Kích hoạt Task Decomposition & MoA Pipeline\n"
            "        LG->>Router: Tổng hợp dữ liệu phân tầng (Hierarchical Reduce)\n"
            "    end\n"
            "    Router->>Router: Kiểm tra Redis Budget & Circuit Breaker (HTTP 429)\n"
            "    Router-->>User: Trả về kết quả JSON cấu trúc nghiêm ngặt"
        )
        return code_flow

    @staticmethod
    def generate_state_machine():
        """
        Sinh sơ đồ trạng thái (Knowledge Lifecycle State Machine) cho KnowledgeUnit.
        """
        state_machine = (
            "stateDiagram-v2\n"
            "    [*] --> Pending : Extracted via Marker/Docling from Doc/Chat\n"
            "    Pending --> Approved : User Review & Approval\n"
            "    Approved --> VectorDB : Auto Index to ChromaDB / Neo4j\n"
            "    Approved --> Rollback : Delete Embedding via Signals"
        )
        return state_machine

    @staticmethod
    def generate_component_diagram():
        """
        Sinh sơ đồ kiến trúc phân hệ theo mô hình Modular Monolith của VnxChatBot,
        tích hợp các thành phần hệ sinh thái mở (n8n, Neo4j, LangGraph, LiteLLM).
        """
        comp_diag = (
            "graph TD\n"
            "    subgraph External_Ecosystem [Hệ sinh thái mở & Giảm tải]\n"
            "        n8n[n8n Workflow Automation] -->|Webhook| Core\n"
            "        Marker[Marker / Docling] -->|Bóc tách File| AIAssistant\n"
            "        Neo4j[(Neo4j Graph DB)] -.->|GraphRAG| AIAssistant\n"
            "    end\n"
            "\n"
            "    subgraph VnxChatBot_Monolith [Kiến trúc Modular Monolith]\n"
            "        Core[apps.core<br/>User & Profile] --> GroupChat[apps.group_chat<br/>Chat & Membership]\n"
            "        GroupChat --> AIAssistant[apps.ai_assistant<br/>RAG & AIFactory]\n"
            "        AIAssistant --> ArchManager[apps.arch_manager<br/>Living Documentation]\n"
            "        GroupChat --> Subscriptions[apps.subscriptions<br/>Gói cước & Giới hạn]\n"
            "    end\n"
            "\n"
            "    subgraph Orchestration_Layer [Điều phối AI]\n"
            "        LiteLLM[LiteLLM Router] -->|Chuẩn hóa API| AIAssistant\n"
            "        LangGraph[LangGraph State Machine] -->|Điều phối MoA| AIAssistant\n"
            "    end\n"
            "\n"
            "    style External_Ecosystem fill:#f9f,stroke:#333,stroke-width:2px\n"
            "    style VnxChatBot_Monolith fill:#bbf,stroke:#333,stroke-width:2px\n"
            "    style Orchestration_Layer fill:#bfb,stroke:#333,stroke-width:2px"
        )
        return comp_diag

    # Bổ sung vào class ArchitectureIntrospectionEngine trong apps/arch_manager/utils.py

    def generate_knowledge_pipeline_flow(self) -> str:
        """Sinh sơ đồ Mermaid biểu diễn luồng xử lý tài liệu và phê duyệt tri thức."""
        return """
        graph TD
            A[User / Admin Upload File] --> B[Document Model Created]
            B -- Signal --> C[Celery Task: process_document_task]
            C --> D[AI_Engine.extract_and_score]
            D --> E[KnowledgeUnit Created: status = pending]
            E --> F{Admin Review}
            F -->|Approve| G[KnowledgeUnit.status = approved]
            F -->|Reject / Delete| H[Cleanup Vector DB]
            G -- Signal --> I[Sync to Vector DB: ChromaDB]
            
            style A fill:#f9fns,stroke:#333,stroke-width:2px
            style E fill:#ff9,stroke:#333,stroke-width:2px
            style G fill:#9f9,stroke:#333,stroke-width:2px
            style I fill:#bbf,stroke:#333,stroke-width:2px
        """.strip()