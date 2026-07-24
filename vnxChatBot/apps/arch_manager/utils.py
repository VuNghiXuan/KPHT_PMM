"""
Module: arch_manager.utils
Author: Kỹ sư Phần mềm Cao cấp / Kiến trúc trưởng VnxChatBot
Description: Engine nội soi mã nguồn (Living Documentation Engine), 
             cung cấp các phương thức sinh sơ đồ Mermaid trực quan theo chuẩn Group-Centric.
             Tích hợp cơ chế Debug Log chi tiết để kiểm soát luồng dữ liệu thời gian thực.
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
        # print("\n" + "--- [DEBUG INTROSPECTION: START GENERATING ERD] ---")
        try:
            from .models import SystemBlueprint
            erd_content = SystemBlueprint.generate_dynamic_erd()
            if erd_content and len(erd_content.strip()) > 15:
                # print(f"✅ [DEBUG ERD SUCCESS]: Đã quét thành công dynamic ERD từ models. Độ dài: {len(erd_content)} chars.")
                # print(f"--- PREVIEW ERD ---\n{erd_content[:300]}...\n-------------------")
                return erd_content
        except Exception as e:
            print(f"❌ [DEBUG ERD ERROR]: Không thể quét dynamic ERD từ models: {str(e)}")

        # print("⚠️ [DEBUG ERD FALLBACK]: Sử dụng ERD tĩnh mặc định.")
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
        Sinh sơ đồ luồng dữ liệu (Code Flow) từ Upload đến LLM RAG Pipeline.
        """
        code_flow = (
            "sequenceDiagram\n"
            "    autonumber\n"
            "    User->>FileProcessor: Upload File (Group-Centric)\n"
            "    FileProcessor->>VectorStore: Embed & Save (Tenant Isolation)\n"
            "    VectorStore->>LLM: RAG Context Retrieval"
        )
        # print(f"🐞 [DEBUG CODE FLOW]: Độ dài {len(code_flow)} chars.")
        return code_flow

    @staticmethod
    def generate_state_machine():
        """
        Sinh sơ đồ trạng thái (Knowledge Lifecycle State Machine) cho KnowledgeUnit.
        """
        state_machine = (
            "stateDiagram-v2\n"
            "    [*] --> Pending : Extracted from Doc/Chat\n"
            "    Pending --> Approved : User Review\n"
            "    Approved --> VectorDB : Auto Index\n"
            "    Approved --> Rollback : Delete Embedding"
        )
        # print(f"🐞 [DEBUG STATE MACHINE]: Độ dài {len(state_machine)} chars.")
        return state_machine

    @staticmethod
    def generate_component_diagram():
        """
        Sinh sơ đồ kiến trúc phân hệ theo mô hình Modular Monolith của VnxChatBot.
        """
        comp_diag = (
            "graph TD\n"
            "    Core[apps.core] --> GroupChat[apps.group_chat]\n"
            "    GroupChat --> AIAssistant[apps.ai_assistant]\n"
            "    AIAssistant --> ArchManager[apps.arch_manager]\n"
            "    GroupChat --> Subscriptions[apps.subscriptions]"
        )
        # print(f"🐞 [DEBUG COMPONENT DIAGRAM]: Độ dài {len(comp_diag)} chars.")
        return comp_diag


    