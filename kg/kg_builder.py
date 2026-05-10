import pandas as pd
from neo4j import GraphDatabase
import os

class NutritionKGBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, params=None):
        with self.driver.session() as session:
            session.run(query, params or {})

    # ------------------ INDEXES ------------------
    def create_indexes(self):
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (f:Food) ON (f.id)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (n:Nutrient) ON (n.id)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (n:Nutrient) ON (n.name)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (b:Biomarker) ON (b.id)")
        self.run_query("CREATE INDEX IF NOT EXISTS FOR (g:Gene) ON (g.symbol)")

    # ------------------ NODE CREATION ------------------

    def create_food_nodes(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            self.run_query("""
                MERGE (f:Food {id:$id})
                SET f.name=$name,
                    f.category=$category,
                    f.serving_size=$size,
                    f.serving_unit=$unit,
                    f.diet_type=$diet_type
            """, {
                "id": r.food_id,
                "name": r.food_name,
                "category": r.category,
                "size": r.serving_size,
                "unit": r.serving_unit,
                "diet_type": r.diet_type
            })

    def create_nutrient_nodes(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            self.run_query("""
                MERGE (n:Nutrient {id:$id})
                SET n.name=$name,
                    n.unit=$unit,
                    n.category=$category
            """, {
                "id": r.nutrient_id,
                "name": r["name"],
                "unit": r.unit,
                "category": r.category
            })

    def create_gene_nodes_from_genenutrient(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            self.run_query("""
                MERGE (g:Gene {symbol:$symbol})
                SET g.full_name=$full_name
            """, {
                "symbol": r["gene_symbol"],
                "full_name": r["gene_fullname"]
            })

    def create_biomarker_nodes(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            self.run_query("""
                MERGE (b:Biomarker {id:$id})
                SET b.name=$name,
                    b.unit=$unit,
                    b.description=$desc
            """, {
                "id": r.biomarker_id,
                "name": r["name"],
                "unit": r.unit,
                "desc": r.description
            })

    def create_biomarker_ranges(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            # Standardizing input: if a value is missing, Neo4j uses the default provided in coalesce
            self.run_query("""
                MATCH (b:Biomarker {id:$id})
                MERGE (range:Range {biomarker_id:$id})
                SET range.name = $name,
                    range.unit = $unit, 
                    range.low_male = coalesce(toFloat($low_male), 0.0),
                    range.high_male = coalesce(toFloat($high_male), 9999.0),
                    range.low_female = coalesce(toFloat($low_female), 0.0),
                    range.high_female = coalesce(toFloat($high_female), 9999.0)
                MERGE (b)-[:HAS_RANGE]->(range)
            """, {
                "id": r.biomarker_id,
                "name": r["name"],
                "unit": str(r.get("unit", "")).strip().lower(),
                "low_male": r.low_male,
                "high_male": r.high_male,
                "low_female": r.low_female,
                "high_female": r.high_female
            })

    # ------------------ RELATIONSHIPS ------------------

    def create_food_nutrient(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            # Skip rows where amount is completely empty (NaN)
            if pd.isna(r.amount):
                continue
                
            self.run_query("""
                MATCH (f:Food {id:$f})
                MATCH (n:Nutrient {id:$n})
                MERGE (f)-[:CONTAINS {
                    amount: coalesce(toFloat($amt), 0.0), 
                    unit: coalesce($unit, "g")
                }]->(n)
            """, {
                "f": r.food_id,
                "n": r.nutrient_id,
                "amt": r.amount,
                "unit": r.unit
            })

    def create_biomarker_nutrient(self, csv):
        df = pd.read_csv(csv)
        for _, r in df.iterrows():
            self.run_query("""
                MATCH (b:Biomarker {id:$b})
                MATCH (n:Nutrient {id:$n})
                MERGE (b)-[:INDICATES]->(n)
            """, {
                "b": r.biomarker_id,
                "n": r.nutrient_id
            })

    def create_gene_nutrient_from_genenutrient(self, csv_file):
        df = pd.read_csv(csv_file)
        for _, r in df.iterrows():
            # Handle multiple IDs like "N011 N002"
            nutrient_ids = str(r["affected_nutrient"]).split()
            
            for n_id in nutrient_ids:
                self.run_query("""
                    MATCH (g:Gene {symbol:$gene})
                    MATCH (n:Nutrient {id:$n_id})
                    MERGE (g)-[:AFFECTS {
                        variant:$variant,
                        interaction_type:$interaction,
                        impact:$impact,
                        action:$action,
                        direction:$direction
                    }]->(n)
                """, {
                    "gene": r["gene_symbol"],
                    "n_id": n_id,
                    "variant": r["variant"],
                    "interaction": r["interaction_type"],
                    "impact": r["impact"],
                    "action": r["action"],
                    "direction": r["direction"]
                })

    # ------------------ RECOMMEND / AVOID ------------------
    def create_recommend_avoid_relationships(self):
        self.run_query("""
        MATCH (b:Biomarker)-[:INDICATES]->(n:Nutrient)<-[c:CONTAINS]-(f:Food)
        // Only link foods that have a measurable amount of the nutrient
        WHERE c.amount > 0
        MERGE (f)-[:POTENTIAL_REMEDY]->(b)
        """)

    # ------------------ CLEAN ------------------
    def clear_graph(self):
        self.run_query("MATCH (n) DETACH DELETE n")


# ------------------ MAIN ------------------
if __name__ == "__main__":
    kg = NutritionKGBuilder(
        "bolt://localhost:7687",
        "neo4j",
        "neo4jabc"
    )


    print("Clearing old data...")
    kg.clear_graph() 

    print("Creating indexes...")
    kg.create_indexes()

    print("Ingesting Nodes...")
    kg.create_food_nodes("data/foods.csv")
    kg.create_nutrient_nodes("data/nutrients.csv")
    kg.create_gene_nodes_from_genenutrient("data/genenutrient.csv")
    kg.create_biomarker_nodes("data/biomarkers.csv")

    # Range Ingestion - File name fixed to biomarkers_maxvalue.csv
    print("Ingesting Biomarker Ranges...")
    kg.create_biomarker_ranges("data/biomarkers_maxvalue.csv")

    print("Creating Relationships...")
    kg.create_food_nutrient("data/food_nutrient_map.csv")
    kg.create_biomarker_nutrient("data/biomarkers.csv")
    kg.create_gene_nutrient_from_genenutrient("data/genenutrient.csv")

    print("Generating Recommendation Shortcut Edges...")
    kg.create_recommend_avoid_relationships()

    print("Success: Knowledge Graph Built with Numeric Integrity.")
    kg.close()