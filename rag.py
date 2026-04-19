from neo4j import GraphDatabase
from datetime import datetime


class NutritionRAG:

    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4jabc"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.last_evidence = []

    def close(self):
        if self.driver:
            self.driver.close()

    def retrieve_context(self, biomarkers, genes, biomarker_recs, gene_recs, diet_preference):

        contexts = []
        self.last_evidence = []

        increase_ids = set()
        decrease_ids = set()

        # ===============================
        # BIOMARKERS
        # ===============================
        for b in biomarker_recs or []:

            n_id = (b.get("nutrient_id") or "").strip().upper()
            if not n_id:
                continue

            direction = b.get("direction")

            if direction == "increase":
                increase_ids.add(n_id)
                self.last_evidence.append(
                    self._build_evidence("biomarker", b.get("name"), n_id, "low", "increase")
                )

            elif direction == "decrease":
                decrease_ids.add(n_id)
                self.last_evidence.append(
                    self._build_evidence("biomarker", b.get("name"), n_id, "high", "decrease")
                )

        # ===============================
        # GENES
        # ===============================
        for g in gene_recs or []:

            n_ids = str(g.get("nutrient_id", "")).upper().split()
            direction = g.get("direction")

            for n_id in n_ids:
                if not n_id:
                    continue

                if direction == "increase":
                    increase_ids.add(n_id)
                    self.last_evidence.append(
                        self._build_evidence("gene", g.get("gene"), n_id, "risk", "increase")
                    )

                elif direction == "decrease":
                    decrease_ids.add(n_id)
                    self.last_evidence.append(
                        self._build_evidence("gene", g.get("gene"), n_id, "sensitivity", "decrease")
                    )

        all_nutrients = list(increase_ids | decrease_ids)

       
        if not all_nutrients:
            return self._macro_based_retrieval(diet_preference)

    
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
                WHEN n.id IN $increase THEN coalesce(toFloat(r.amount), 0) * 2
                WHEN n.id IN $decrease THEN coalesce(toFloat(r.amount), 0) * -3
                ELSE 0
            END AS score

            WITH f,
                 collect({
                    id: n.id,
                    name: n.name,
                    amount: coalesce(toFloat(r.amount), 0)
                 }) AS nutrient_data,
                 SUM(score) AS total_score

            RETURN f.name AS food, nutrient_data, total_score
            ORDER BY total_score DESC
            LIMIT 15
            """

            result = session.run(query, {
                "increase": list(increase_ids),
                "decrease": list(decrease_ids),
                "all_nutrients": all_nutrients,
                "diet_pref": (diet_preference or "vegetarian").lower()
            })

            for row in result:

                nutrients = row.get("nutrient_data") or []

                contexts.append({
                    "food": row.get("food"),
                    "score": round(row.get("total_score", 0), 2),
                    "nutrients": nutrients,
                    "reason": self._generate_reason(nutrients, increase_ids, decrease_ids)
                })

        return contexts


    def _macro_based_retrieval(self, diet_preference):

        contexts = []

        with self.driver.session() as session:

            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)

            WHERE n.name IN ['Net Protein', 'Total Carbohydrates', 'Saturated Fat']
            AND (
                $diet_pref = 'non-vegetarian'
                OR f.diet_type = 'Vegetarian'
            )

            WITH f,
            SUM(
                CASE
                    WHEN n.name = 'Net Protein' THEN coalesce(toFloat(r.amount),0) * 2.5
                    WHEN n.name = 'Total Carbohydrates' THEN coalesce(toFloat(r.amount),0) * 1.2
                    WHEN n.name = 'Saturated Fat' THEN coalesce(toFloat(r.amount),0) * -2
                    ELSE 0
                END
            ) AS score,

            collect({
                id:n.id,
                name:n.name,
                amount:coalesce(toFloat(r.amount),0)
            }) AS nutrient_data

            RETURN f.name AS food, score, nutrient_data
            ORDER BY score DESC
            LIMIT 15
            """

            result = session.run(query, {
                "diet_pref": (diet_preference or "vegetarian").lower()
            })

            for row in result:
                contexts.append({
                    "food": row.get("food"),
                    "score": round(row.get("score", 0), 2),
                    "nutrients": row.get("nutrient_data", []),
                    "reason": "Macro-balanced food"
                })

        return contexts

    # ===============================
    def _generate_reason(self, nutrient_data, increase, decrease):

        reasons = []

        for n in nutrient_data:
            nid = n.get("id")

            if nid in increase:
                reasons.append(f"Rich in {n.get('name')}")

            elif nid in decrease:
                reasons.append(f"Low in {n.get('name')}")

        return ", ".join(reasons[:2]) if reasons else "Supports overall nutrition"

    # ===============================
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