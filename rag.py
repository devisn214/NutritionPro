from neo4j import GraphDatabase
from datetime import datetime, timezone
from nutrition_engine.biomarker_interaction import get_biomarker_interactions


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

        # ================= BIOMARKERS =================
        for b in biomarker_recs or []:

            n_id = (b.get("nutrient_id") or "").strip().upper()
            direction = b.get("direction")

            if not n_id or not direction:
                continue

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

        # ================= GENES =================
        for g in gene_recs or []:

            n_ids = str(g.get("nutrient_id", "")).upper().split()
            direction = g.get("direction")

            for n_id in n_ids:

                if not n_id or not direction:
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

        # ================= INTERACTIONS =================
        interaction_result = get_biomarker_interactions(biomarkers)

        increase_ids.update(interaction_result.get("increase", set()))
        decrease_ids.update(interaction_result.get("decrease", set()))

        for note in interaction_result.get("notes", []):
            self.last_evidence.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "interaction",
                "trigger": "multi-biomarker",
                "nutrient_id": "",
                "status": "combined",
                "action": note,
                "logic_path": note
            })

        # ================= FINAL NUTRIENTS =================
        final_increase = increase_ids - decrease_ids
        final_decrease = decrease_ids

        all_nutrients = list(final_increase | final_decrease)

        reward_categories, penalty_categories = self._get_category_rules(biomarker_recs)

        if not all_nutrients:
            return self._macro_based_retrieval(
                diet_preference,
                reward_categories,
                penalty_categories
            )

        # ================= MAIN QUERY =================
        with self.driver.session() as session:

            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)

            WHERE n.id IN $all_nutrients
            AND toLower(n.name) <> 'cholesterol (total)'
            AND NOT toLower(f.category) IN ['spice','masala','condiment','seasoning']
            AND (
                $diet_pref = 'non-vegetarian'
                OR f.diet_type = 'Vegetarian'
            )

            WITH f, n, r,

            CASE
                WHEN n.id IN $increase THEN coalesce(toFloat(r.amount),0) * 1.5
                WHEN n.id IN $decrease THEN coalesce(toFloat(r.amount),0) * -1.2
                ELSE 0
            END AS nutrient_score

            WITH f,
                 collect({
                    id:n.id,
                    name:n.name,
                    amount:coalesce(toFloat(r.amount),0)
                 }) AS nutrient_data,
                 SUM(nutrient_score) AS base_score

            WITH f, nutrient_data, base_score,

            CASE
                WHEN toLower(f.category) IN $reward_categories THEN 18
                ELSE 0
            END +

            CASE
                WHEN toLower(f.category) IN $penalty_categories THEN -25
                ELSE 0
            END AS category_score

            RETURN
                f.name AS food,
                nutrient_data,
                (base_score + category_score) AS total_score
            """

            result = session.run(
                query,
                {
                    "increase": list(final_increase),
                    "decrease": list(final_decrease),
                    "all_nutrients": all_nutrients,
                    "diet_pref": (diet_preference or "vegetarian").lower(),
                    "reward_categories": reward_categories,
                    "penalty_categories": penalty_categories
                }
            )

            raw_results = []

            for row in result:

                nutrients = row.get("nutrient_data") or []
                score = round(row.get("total_score", 0), 2)

                for n in nutrients:
                    name = (n.get("name") or "").lower()
                    amt = float(n.get("amount", 0) or 0)

                    if any(x in name for x in ["omega-3", "monounsaturated", "polyunsaturated"]):
                        score += amt * 0.5

                raw_results.append({
                    "food": row.get("food"),
                    "score": score,
                    "nutrients": nutrients,
                    "reason": self._generate_reason(
                        nutrients,
                        final_increase,
                        final_decrease
                    )
                })

            # ================= ✅ CRITICAL FIX =================
            # If Neo4j returns nothing → fallback query
            if not raw_results:

                fallback_query = """
                MATCH (f:Food)
                WHERE NOT toLower(f.category) IN ['spice','masala','condiment','seasoning']
                AND (
                    $diet_pref = 'non-vegetarian'
                    OR f.diet_type = 'Vegetarian'
                )
                RETURN f.name AS food
                LIMIT 50
                """

                fallback_result = session.run(
                    fallback_query,
                    {"diet_pref": (diet_preference or "vegetarian").lower()}
                )

                raw_results = [
                    {
                        "food": row.get("food"),
                        "score": 1,
                        "nutrients": [],
                        "reason": "General healthy option"
                    }
                    for row in fallback_result
                ]

            # ================= FILTER =================
            BLOCK_FOODS = ["liver", "organ", "gizzard"]

            raw_results = [
                f for f in raw_results
                if not any(b in f["food"].lower() for b in BLOCK_FOODS)
            ]

            MIN_SCORE_THRESHOLD = 5

            contexts = [
                f for f in raw_results
                if f["score"] > MIN_SCORE_THRESHOLD
            ]

            if not contexts:
                contexts = sorted(raw_results, key=lambda x: x["score"], reverse=True)[:10]
            else:
                contexts = sorted(contexts, key=lambda x: x["score"], reverse=True)[:15]

        return contexts

    # ================= CATEGORY RULES =================
    def _get_category_rules(self, biomarker_recs):

        reward = set()
        penalty = set()

        status = {}

        for b in biomarker_recs or []:
            name = str(b.get("name", "")).strip().lower()
            val = str(b.get("status", "")).strip().lower()
            status[name] = val

        if status.get("ldl cholesterol") == "high":
            penalty.update(["oil", "dairy", "meat", "sweet"])
            reward.update(["fish", "leaf", "legume", "grain", "nut", "seed"])

        if status.get("hdl cholesterol") == "low":
            penalty.update(["sweet", "grain", "oil"])
            reward.update(["fish", "nut", "seed", "leaf", "legume"])

        if status.get("total cholesterol") == "high":
            penalty.update(["oil", "dairy", "meat", "sweet"])
            reward.update(["fish", "leaf", "legume"])

        if status.get("triglycerides") == "high":
            penalty.update(["sweet", "grain", "tuber", "oil"])
            reward.update(["fish", "leaf", "veg", "legume"])

        if status.get("hba1c") == "high":
            penalty.update(["sweet", "grain", "tuber"])
            reward.update(["leaf", "veg", "legume", "fish", "egg"])

        if status.get("fasting glucose") == "high":
            penalty.update(["sweet", "grain", "fruit", "tuber"])
            reward.update(["leaf", "veg", "legume", "fish", "egg"])

        if status.get("uric acid") == "high":
            penalty.update(["meat", "seafood", "sweet"])
            reward.update(["veg", "fruit", "dairy", "drink"])

        if status.get("serum sodium") == "high":
            penalty.update(["seafood", "dairy", "meat", "sweet"])
            reward.update(["fruit", "veg", "drink", "leaf"])

        return list(reward), list(penalty)

    # ================= FALLBACK =================
    def _macro_based_retrieval(self, diet_preference, reward_categories, penalty_categories):

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
                    WHEN n.name = 'Net Protein'
                        THEN coalesce(toFloat(r.amount),0) * 2.5
                    WHEN n.name = 'Total Carbohydrates'
                        THEN coalesce(toFloat(r.amount),0) * 1.2
                    WHEN n.name = 'Saturated Fat'
                        THEN coalesce(toFloat(r.amount),0) * -2
                    ELSE 0
                END
            ) AS macro_score

            WITH f, macro_score,

            CASE
                WHEN toLower(f.category) IN $reward_categories THEN 18
                ELSE 0
            END +

            CASE
                WHEN toLower(f.category) IN $penalty_categories THEN -25
                ELSE 0
            END AS category_score

            RETURN
                f.name AS food,
                (macro_score + category_score) AS score
            """

            result = session.run(
                query,
                {
                    "diet_pref": (diet_preference or "vegetarian").lower(),
                    "reward_categories": reward_categories,
                    "penalty_categories": penalty_categories
                }
            )

            raw = []

            for row in result:
                raw.append({
                    "food": row.get("food"),
                    "score": round(row.get("score", 0), 2),
                    "nutrients": [],
                    "reason": "Macro-balanced food"
                })

            contexts = [f for f in raw if f["score"] > 5]

            if not contexts:
                contexts = sorted(raw, key=lambda x: x["score"], reverse=True)[:10]
            else:
                contexts = sorted(contexts, key=lambda x: x["score"], reverse=True)[:15]

        return contexts

    def _generate_reason(self, nutrient_data, increase, decrease):

        reasons = []

        for n in nutrient_data:

            nid = n.get("id")

            if nid in increase:
                reasons.append(f"Rich in {n.get('name')}")
            elif nid in decrease:
                reasons.append(f"Low in {n.get('name')}")

        return ", ".join(reasons[:2]) if reasons else "Supports overall nutrition"

    def _build_evidence(self, source, name, n_id, status, action):

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "trigger": name,
            "nutrient_id": n_id,
            "status": status,
            "action": action,
            "logic_path": f"{source.upper()} ({name}) → {n_id} → {action}"
        }