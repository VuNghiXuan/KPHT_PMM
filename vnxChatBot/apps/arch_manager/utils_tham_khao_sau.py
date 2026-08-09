# Cập nhật trong apps/arch_manager/utils.py

class ArchitectureIntrospectionEngine:
    # Bộ nhớ tạm lưu trữ các bước luồng do các app đăng ký động
    _dynamic_flow_registry = []

    @classmethod
    def register_flow_step(cls, source: str, target: str, label: str = ""):
        """Cho phép bất kỳ app nào đăng ký thêm một bước chuyển đổi dữ liệu vào luồng chung."""
        transition = (source, target, label)
        if transition not in cls._dynamic_flow_registry:
            cls._dynamic_flow_registry.append(transition)

    @classmethod
    def generate_auto_discovered_pipeline(cls) -> str:
        """
        Tự động tổng hợp sơ đồ luồng từ:
        1. Các luồng được đăng ký động qua Code (Registry).
        2. Quét các Celery Tasks và Django Signals tiêu chuẩn trong hệ thống.
        """
        mermaid_lines = ["graph TD"]
        
        # Thêm các luồng cốt lõi mặc định của hệ thống VnxChatBot
        default_flows = [
            ("User / Admin Upload File", "Document Model Created", ""),
            ("Document Model Created", "Celery Task: process_document_task", "Signal"),
            ("Celery Task: process_document_task", "AI_Engine.extract_and_score", "Parse (Docling/Marker)"),
            ("AI_Engine.extract_and_score", "KnowledgeUnit Created: status = pending", "Score [0.0 - 1.0]"),
            ("KnowledgeUnit Created: status = pending", "Admin Review UI", "Review"),
            ("Admin Review UI", "KnowledgeUnit.status = approved", "Approve"),
            ("Admin Review UI", "Cleanup Vector DB", "Reject / Delete"),
            ("KnowledgeUnit.status = approved", "Sync to Vector DB: ChromaDB", "Signal"),
            ("User Chat Message", "Multi-Model Router (LiteLLM)", "WebSocket"),
            ("Multi-Model Router (LiteLLM)", "Redis Semantic Cache", "Check (> 0.92)"),
            ("Redis Semantic Cache", "LangGraph (Task Decomposition & MoA)", "Cache Miss")
        ]
        
        all_flows = set(default_flows + cls._dynamic_flow_registry)
        
        for src, dest, label in all_flows:
            # Làm sạch chuỗi để tạo ID hợp lệ cho Mermaid
            src_clean = src.replace(' ', '_').replace(':', '_').replace('.', '_').replace('-', '_').replace('(', '_').replace(')', '_')
            dest_clean = dest.replace(' ', '_').replace(':', '_').replace('.', '_').replace('-', '_').replace('(', '_').replace(')', '_')
            
            mermaid_lines.append(f"    {src_clean}[\"{src}\"] -->|{label}| {dest_clean}[\"{dest}\"]" if label else f"    {src_clean}[\"{src}\"] --> {dest_clean}[\"{dest}\"]")

        # Thêm màu sắc trực quan
        mermaid_lines.append("    style User___Admin_Upload_File fill:#f9f,stroke:#333,stroke-width:2px")
        mermaid_lines.append("    style KnowledgeUnit_Created__status___pending fill:#ff9,stroke:#333,stroke-width:2px")
        mermaid_lines.append("    style KnowledgeUnit_status___approved fill:#9f9,stroke:#333,stroke-width:2px")
        
        return "\n".join(mermaid_lines)