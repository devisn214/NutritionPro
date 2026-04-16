from neo4j import GraphDatabase
from datetime import datetime

class NutritionRAG:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4jabc"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.last_evidence = []

    def close(self):
        self.driver.close()

    def retrieve_context(self, biomarkers, genes, biomarker_recs, gene_recs, diet_preference):
        contexts = []
        self.last_evidence = []
        increase_ids = set()
        decrease_ids = set()

  
        for b in biomarker_recs:
            n_id = b.get("nutrient_id")
            if not n_id: continue
            n_id = n_id.strip().upper()
            if b.get("direction") == "increase":
                increase_ids.add(n_id)
                self.last_evidence.append(self._build_evidence("biomarker", b.get("name"), n_id, "low", "increase"))
            elif b.get("direction") == "decrease":
                decrease_ids.add(n_id)
                self.last_evidence.append(self._build_evidence("biomarker", b.get("name"), n_id, "high", "decrease"))

        for g in gene_recs:
            n_ids_str = g.get("nutrient_id")
            if not n_ids_str: continue
            n_ids = str(n_ids_str).strip().upper().split()
            for n_id in n_ids:
                if g.get("direction") == "increase":
                    increase_ids.add(n_id)
                    self.last_evidence.append(self._build_evidence("gene", g.get("gene"), n_id, "risk variant", "increase"))
                elif g.get("direction") == "decrease":
                    decrease_ids.add(n_id)
                    self.last_evidence.append(self._build_evidence("gene", g.get("gene"), n_id, "sensitivity", "decrease"))

        all_nutrient_ids = list(increase_ids | decrease_ids)
        if not all_nutrient_ids: 
            return []

        with self.driver.session() as session:
       
            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)
            WHERE n.id IN $all_nutrients
            AND (
                $diet_pref = 'non-vegetarian' 
                OR f.diet_type = 'Vegetarian'
            )
            WITH f, n, r,
            CASE 
                WHEN n.id IN $increase THEN toFloat(r.amount) * 1.5
                WHEN n.id IN $decrease THEN toFloat(r.amount) * -3.0
                ELSE 0
            END AS score
            WITH f,
                 collect({id: n.id, name: n.name, amount: toFloat(r.amount)}) AS nutrient_data,
                 SUM(score) AS total_score
            WHERE NONE(nt IN nutrient_data WHERE nt.id IN $decrease AND nt.amount > 0.5)
            RETURN f.name AS food, nutrient_data, total_score
            ORDER BY total_score DESC LIMIT 12
            """
            
            result = session.run(query, {
                "increase": list(increase_ids),
                "decrease": list(decrease_ids),
                "all_nutrients": all_nutrient_ids,
                "diet_pref": diet_preference.lower()
            })

            for row in result:
                contexts.append({
                    "food": row["food"],
                    "score": round(row["total_score"], 2),
                    "nutrients": row["nutrient_data"],
                    "reason": self._generate_reason(row["nutrient_data"], increase_ids, decrease_ids)
                })
        
        return contexts

    def _generate_reason(self, nutrient_data, increase, decrease):
        reasons = [f"High {n['name']}" for n in nutrient_data if n['id'] in increase]
        return ", ".join(reasons[:2])

    def _build_evidence(self, source, name, n_id, status, action):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source, 
            "trigger": name, 
            "nutrient_id": n_id,
            "status": status, 
            "action": action,
            "logic_path": f"{source.upper()} ({name}) → {n_id} → {action}"
        }