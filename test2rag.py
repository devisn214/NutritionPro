
from neo4j import GraphDatabase

class NutritionRAG:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4jabc"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def retrieve_context(self, biomarkers, genes):
        contexts = []

        with self.driver.session() as session:

            for b in biomarkers:
                result = session.run(
                    """
                    MATCH (bm:Biomarker)-[:INDICATES]->(n:Nutrient)
                    WHERE toLower(bm.name) = toLower($bname)
                    MATCH (f:Food)-[:CONTAINS]->(n)
                    OPTIONAL MATCH (n)-[r:INTERACTS_WITH]->(g:Gene)
                    RETURN
                        bm.name AS biomarker,
                        n.name AS nutrient,
                        collect(DISTINCT f.name)[0..5] AS foods,
                        collect(DISTINCT {
                            gene: g.symbol,
                            interaction: coalesce(r.interaction_type, ""),
                            impact: coalesce(r.impact_description, "")
                        })[0..3] AS genes
                    LIMIT 3
                    """,
                    {"bname": b["name"]}
                )

                for row in result:
                    contexts.append({
                        "biomarker": row["biomarker"],
                        "nutrient": row["nutrient"],
                        "foods": row["foods"],
                        "genes": [g for g in row["genes"] if g["gene"]]
                    })

          
            for g in genes:
                result = session.run(
                    """
                    MATCH (gen:Gene)-[:MODULATES]->(n:Nutrient)
                    WHERE toLower(gen.symbol) = toLower($gsymbol)
                    OPTIONAL MATCH (f:Food)-[:CONTAINS]->(n)
                    RETURN
                        gen.symbol AS gene,
                        n.name AS nutrient,
                        collect(DISTINCT f.name)[0..5] AS foods
                    LIMIT 3
                    """,
                    {"gsymbol": g["name"]}
                )

                for row in result:
                    contexts.append({
                        "biomarker": None,
                        "nutrient": row["nutrient"],
                        "foods": row["foods"],
                        "genes": [{"gene": row["gene"], "interaction": "", "impact": ""}]
                    })

        return contexts



