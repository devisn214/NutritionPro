from neo4j import GraphDatabase

class NutritionRAG:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4jabc"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def retrieve_context(self, biomarkers, genes, biomarker_recs, gene_recs):
        contexts = []

        bio_status = {b["biomarker"]: b["status"] for b in biomarker_recs}
        gene_status = {g["gene"]: g["reason"] for g in gene_recs}

        with self.driver.session() as session:

            #  BIOMARKERS 
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
                    LIMIT 6
                    """,
                    {"bname": b["name"]}
                )

                for row in result:
                    status = bio_status.get(row["biomarker"], "Normal")
                    action = "increase" if status == "Low/Deficient" else "reduce" if status == "High/Excess" else "maintain"

                    contexts.append({
                        "biomarker": row["biomarker"],
                        "nutrient": row["nutrient"],
                        "status": status,
                        "action": action,
                        "foods": row["foods"],
                        "genes": [g for g in row["genes"] if g["gene"]]
                    })

            #  GENES 
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
                    status = gene_status.get(row["gene"], "Normal")

                    contexts.append({
                        "gene": row["gene"],
                        "nutrient": row["nutrient"],
                        "gene_status": status,
                        "action": "increase" if "Reduced" in status else "maintain",
                        "foods": row["foods"]
                    })

        return contexts
    
    
    
'''
if __name__ == "__main__":
    rag = NutritionRAG()
    context = rag.retrieve_context(
        [{"name": "urinary pantothenate"}], [] 
    )
    print("RAG CONTEXT:", context)
    rag.close()'''