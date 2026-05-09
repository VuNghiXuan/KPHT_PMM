import os
import re
from neo4j import GraphDatabase
from pathlib import Path
from dotenv import load_dotenv

# load_dotenv()
# Tự động tìm đường dẫn thư mục gốc (ChatBot)
BASE_DIR = Path(__file__).resolve().parent.parent.parent 
# print('-------------BASE_DIR', BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))
# print('-------------load_dotenv(os.path.join(BASE_DIR, ".env"))', load_dotenv(os.path.join(BASE_DIR, ".env")))

class Neo4jService:
    def __init__(self):
        # In ra để kiểm tra ngay trong Terminal khi chạy
        url = os.getenv("NEO4J_URL")
        print(f"--- DEBUG NEO4J_URL: '{url}' ---") 

        if not url:
            # Nếu vẫn rỗng, ép nó dùng localhost để chạy tiếp
            url = "bolt://localhost:7687"
            print("--- WARNING: Không đọc được .env, dùng default localhost ---")

        self.driver = GraphDatabase.driver(
            url, 
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), 
                  os.getenv("NEO4J_PASSWORD", "kpht2026"))
        )



    def close(self):
        self.driver.close()

    def sync_full_logic(self, project_obj):
        """
        Hàm tổng lực: Đồng bộ từ Project -> Sheet -> DataField
        """
        with self.driver.session() as session:
            # BƯỚC 1: Đồng bộ Project và danh sách Sheet
            sheets_data = [
                {"id": s.id, "name": s.name, "category": getattr(s, 'category', '')} 
                for s in project_obj.sheets.all()
            ]
            
            session.run("""
                MERGE (p:Project {id: $p_id}) 
                SET p.name = $p_name, p.updated_at = datetime()
                WITH p
                UNWIND $sheets as s_data
                MERGE (s:Sheet {id: s_data.id}) 
                SET s.name = s_data.name, s.category = s_data.category
                MERGE (p)-[:HAS_SHEET]->(s)
            """, p_id=project_obj.id, p_name=project_obj.name, sheets=sheets_data)

            # BƯỚC 2: Đồng bộ DataField theo từng Sheet (Xử lý Batch để tránh treo RAM)
            for sheet in project_obj.sheets.all():
                fields = sheet.fields.all() # Giả sử quan hệ là sheet.fields
                total = fields.count()
                batch_size = 5000  # Mỗi lần nạp 5000 ô
                
                for i in range(0, total, batch_size):
                    batch_fields = fields[i:i+batch_size]
                    fields_payload = [
                        {
                            "id": f.id,
                            "address": f.cell_address,
                            "value": str(f.value) if f.value else "",
                            "formula": f.formula or "",
                            "label": f.label or ""
                        } for f in batch_fields
                    ]
                    
                    session.run("""
                        MATCH (s:Sheet {id: $s_id})
                        UNWIND $fields as f_data
                        MERGE (f:DataField {id: f_data.id})
                        SET f.address = f_data.address,
                            f.value = f_data.value,
                            f.formula = f_data.formula,
                            f.label = f_data.label
                        MERGE (s)-[:CONTAINS]->(f)
                    """, s_id=sheet.id, fields=fields_payload)
                    
        return True

    def create_dependency(self, source_id, target_id):
        """
        Tạo quan hệ DEPENDS_ON giữa 2 ô (Dùng cho logic công thức)
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (a:DataField {id: $a_id})
                MATCH (b:DataField {id: $b_id})
                MERGE (a)-[:DEPENDS_ON]->(b)
            """, a_id=source_id, b_id=target_id)
    
    

    def parse_formula_dependencies(self, sheet_obj):
        """
        Tìm các ô liên quan trong công thức và tạo mũi tên trong Neo4j
        """
        # Regex tìm địa chỉ ô như A1, B10, $C$15...
        cell_regex = r'\b[A-Z]+\d+\b' 
        
        fields_with_formula = sheet_obj.fields.exclude(formula="")
        
        for field in fields_with_formula:
            # Tìm tất cả địa chỉ ô xuất hiện trong công thức
            dependencies = re.findall(cell_regex, field.formula)
            
            for dep_address in dependencies:
                # Tìm ID của ô phụ thuộc trong cùng 1 Sheet
                target_field = sheet_obj.fields.filter(cell_address=dep_address).first()
                if target_field:
                    self.create_dependency(field.id, target_field.id)