import pandas as pd
from neo4j import GraphDatabase


class NutritionKGBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, params=None):
        with self.driver.session() as session:
            session.run(query, params or {})

    def create_food_nodes(self, foods_csv):
        df = pd.read_csv(foods_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MERGE (f:Food {id:$id})
                SET f.name=$name,
                    f.category=$category,
                    f.serving_size=$serving_size,
                    f.serving_unit=$serving_unit
                """,
                {
                    "id": row.food_id,
                    "name": row.food_name,
                    "category": row.category,
                    "serving_size": row.serving_size,
                    "serving_unit": row.serving_unit
                }
            )

    def create_nutrient_nodes(self, nutrients_csv):
        df = pd.read_csv(nutrients_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MERGE (n:Nutrient {id:$id})
                SET n.name=$name,
                    n.unit=$unit,
                    n.category=$category
                """,
                {
                    "id": row.nutrient_id,
                    "name": row["name"],
                    "unit": row.unit,
                    "category": row.category
                }
            )

    def create_biomarker_nodes(self, biomarkers_csv):
        df = pd.read_csv(biomarkers_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MERGE (b:Biomarker {id:$id})
                SET b.name=$name,
                    b.unit=$unit,
                    b.description=$description
                """,
                {
                    "id": row.biomarker_id,
                    "name":str(row["name"]).lower(),
                    "unit": row.unit,
                    "description": row.description
                }
            )

    def create_gene_nodes(self, genes_csv):
        df = pd.read_csv(genes_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MERGE (g:Gene {symbol:$symbol})
                SET g.id=$id,
                    g.full_name=$full_name,
                    g.description=$description
                """,
                {
                    "id": row.gene_id,
                    "symbol": row.gene_symbol,
                    "full_name": row.full_name,
                    "description": row.description
                }
            )

    def create_food_nutrient_relationships(self, food_nutrient_csv):
        df = pd.read_csv(food_nutrient_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MATCH (f:Food {id:$food_id})
                MATCH (n:Nutrient {id:$nutrient_id})
                MERGE (f)-[:CONTAINS {
                    amount:$amount,
                    unit:$unit
                }]->(n)
                """,
                {
                    "food_id": row.food_id,
                    "nutrient_id": row.nutrient_id,
                    "amount": row.amount,
                    "unit": row.unit
                }
            )

    def create_biomarker_nutrient_relationships(self, biomarkers_csv):
        df = pd.read_csv(biomarkers_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MATCH (b:Biomarker {id:$biomarker_id})
                MATCH (n:Nutrient {id:$nutrient_id})
                MERGE (b)-[:INDICATES]->(n)
                """,
                {
                    "biomarker_id": row.biomarker_id,
                    "nutrient_id": row.nutrient_id
                }
            )

    def create_nutrient_gene_relationships(self, nutrient_gene_csv):
        df = pd.read_csv(nutrient_gene_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MATCH (n:Nutrient {name:$nutrient_name})
                MATCH (g:Gene {gene_name:$full_name})
                MERGE (n)-[:INTERACTS_WITH {
                    interaction_type:$interaction_type,
                    impact_description:$impact_description
                }]->(g)
                """,
                {
                    "nutrient_name": row.nutrient_name,
                    "gene_name": row.full_name,
                    "interaction_type": row.interaction_type,
                    "impact_description": row.impact_description
                }
            )

    def create_gene_modulation_relationships(self, nutrient_gene_csv):
        df = pd.read_csv(nutrient_gene_csv)
        for _, row in df.iterrows():
            self.run_query(
                """
                MATCH (g:Gene {symbol:$gene_symbol})
                MATCH (n:Nutrient {name:$nutrient_name})
                MERGE (g)-[:MODULATES]->(n)
                """,
                {
                    "gene_symbol": row.gene_symbol,
                    "nutrient_name": row.nutrient_name
                }
            )


if __name__ == "__main__":
    kg = NutritionKGBuilder(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="neo4jabc"
    )

    kg.create_food_nodes("data/foods.csv")
    kg.create_nutrient_nodes("data/nutrients.csv")
    kg.create_biomarker_nodes("data/biomarkers.csv")
    kg.create_gene_nodes("data/genes.csv")

    kg.create_food_nutrient_relationships("data/food_nutrient_map.csv")
    kg.create_biomarker_nutrient_relationships("data/biomarkers.csv")
    kg.create_nutrient_gene_relationships("data/nutrient_gene_map.csv")
    kg.create_gene_modulation_relationships("data/nutrient_gene_map.csv")

    kg.close()
