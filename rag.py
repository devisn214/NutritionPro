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

    # =========================================================
    # MAIN RETRIEVAL (GLOBAL SCORING - FIXED)
    # =========================================================
    def retrieve_context(self, biomarkers, genes, biomarker_recs, gene_recs, diet_preference):

        self.last_evidence = []

        increase_ids = set()
        decrease_ids = set()

        # =====================================================
        # BIOMARKER PROCESSING
        # =====================================================
        for b in biomarker_recs or []:

            nutrient_ids = str(b.get("nutrient_id", "")).upper().split()
            direction = str(b.get("direction", "")).lower()

            for nid in nutrient_ids:

                nid = nid.strip()
                if not nid:
                    continue

                if direction in ["increase", "maintain", "support"]:

                    increase_ids.add(nid)

                    self.last_evidence.append(
                        self._build_evidence(
                            "biomarker",
                            b.get("name"),
                            nid,
                            "low",
                            direction
                        )
                    )

                elif direction == "decrease":

                    decrease_ids.add(nid)

                    self.last_evidence.append(
                        self._build_evidence(
                            "biomarker",
                            b.get("name"),
                            nid,
                            "high",
                            "decrease"
                        )
                    )

        # =====================================================
        # GENE PROCESSING
        # =====================================================
        for g in gene_recs or []:

            nutrient_ids = str(g.get("nutrient_id", "")).upper().split()
            direction = str(g.get("direction", "")).lower()

            for nid in nutrient_ids:

                nid = nid.strip()
                if not nid:
                    continue

                if direction in ["increase", "maintain", "support"]:

                    increase_ids.add(nid)

                    self.last_evidence.append(
                        self._build_evidence(
                            "gene",
                            g.get("gene"),
                            nid,
                            "genetic",
                            direction
                        )
                    )

                elif direction == "decrease":

                    decrease_ids.add(nid)

                    self.last_evidence.append(
                        self._build_evidence(
                            "gene",
                            g.get("gene"),
                            nid,
                            "sensitivity",
                            "decrease"
                        )
                    )

        # =====================================================
        # INTERACTION LAYER
        # =====================================================
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

        # =====================================================
        # SAFE CONFLICT RESOLUTION
        # =====================================================
        overlap = increase_ids & decrease_ids

        increase_ids = increase_ids - overlap
        decrease_ids = decrease_ids - overlap

        reward_categories, penalty_categories = self._get_category_rules(biomarkers)

        # =====================================================
        # GLOBAL SCORING QUERY (FIXED GROUPING)
        # =====================================================
        with self.driver.session() as session:

            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)

            WHERE NOT toLower(f.category) IN [
                'spice','masala','condiment','seasoning'
            ]

            AND (
                $diet_pref = 'non-vegetarian'
                OR f.diet_type = 'Vegetarian'
            )

            WITH f, n,
                 coalesce(toFloat(r.amount),0) AS amount

            WITH f,
                 collect({
                    id: n.id,
                    name: n.name,
                    amount: amount
                 }) AS nutrient_data,

                 SUM(
                    CASE
                        WHEN n.id IN $increase_ids AND n.id IN $decrease_ids
                            THEN -log(amount + 1)

                        WHEN n.id IN $increase_ids
                            THEN log(amount + 1)

                        WHEN n.id IN $decrease_ids
                            THEN -2 * log(amount + 1)

                        ELSE 0
                    END
                 ) AS nutrient_score,

                 CASE
                    WHEN toLower(f.category) IN $reward_categories THEN 18
                    ELSE 0
                 END +

                 CASE
                    WHEN toLower(f.category) IN $penalty_categories THEN -25
                    ELSE 0
                 END AS category_score

            WITH f, nutrient_data,
                 (nutrient_score + category_score) AS total_score

            RETURN
                f.name AS food,
                nutrient_data,
                total_score

            ORDER BY total_score DESC
            LIMIT 15
            """

            result = session.run(
                query,
                {
                    "diet_pref": (diet_preference or "vegetarian").lower(),
                    "increase_ids": list(increase_ids),
                    "decrease_ids": list(decrease_ids),
                    "reward_categories": reward_categories,
                    "penalty_categories": penalty_categories
                }
            )

            balanced_results = []

            for row in result:

                food = row.get("food")
                if not food:
                    continue

                nutrients = row.get("nutrient_data") or []

                balanced_results.append({
                    "food": food,
                    "score": round(float(row.get("total_score", 0)), 2),
                    "nutrients": nutrients,
                    "reason": self._generate_reason_for_target(
                        nutrients,
                        increase_ids,
                        decrease_ids
                    )
                })

        # =====================================================
        # FALLBACK
        # =====================================================
        if not balanced_results:

            return self._macro_based_retrieval(
                diet_preference,
                reward_categories,
                penalty_categories
            )

        return balanced_results

    # =========================================================
    # CATEGORY RULES (UNCHANGED)
    # =========================================================
    def _get_category_rules(self, biomarkers):

        reward = set()
        penalty = set()

        status = {}

        for b in biomarkers or []:

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

    # =========================================================
    # MACRO FALLBACK
    # =========================================================
    def _macro_based_retrieval(self, diet_preference, reward_categories, penalty_categories):

        with self.driver.session() as session:

            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)

            WHERE n.name IN [
                'Net Protein',
                'Total Carbohydrates',
                'Saturated Fat'
            ]

            AND (
                $diet_pref = 'non-vegetarian'
                OR f.diet_type = 'Vegetarian'
            )

            WITH f,

            collect({
                id:n.id,
                name:n.name,
                amount:coalesce(toFloat(r.amount),0)
            }) AS nutrient_data,

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

            WITH f, nutrient_data,
                 (macro_score +
                  CASE WHEN toLower(f.category) IN $reward_categories THEN 18 ELSE 0 END +
                  CASE WHEN toLower(f.category) IN $penalty_categories THEN -25 ELSE 0 END
                 ) AS score

            RETURN f.name AS food, nutrient_data, score
            ORDER BY score DESC
            LIMIT 15
            """

            result = session.run(
                query,
                {
                    "diet_pref": (diet_preference or "vegetarian").lower(),
                    "reward_categories": reward_categories,
                    "penalty_categories": penalty_categories
                }
            )

            return [
                {
                    "food": row.get("food"),
                    "score": row.get("score"),
                    "nutrients": row.get("nutrient_data", []),
                    "reason": "Macro-balanced food"
                }
                for row in result
            ]

    # =========================================================
    # FIXED EXPLANATION FUNCTION (RESTORED)
    # =========================================================
    def _generate_reason_for_target(self, nutrient_data, increase_ids, decrease_ids):

        rich = []
        low = []

        for n in nutrient_data:

            nid = str(n.get("id", "")).upper()
            name = n.get("name", "")

            if nid in increase_ids:
                rich.append(name)

            if nid in decrease_ids:
                low.append(name)

        if rich and low:
            return f"Rich in {', '.join(rich[:3])} | Lower in {', '.join(low[:3])}"

        if rich:
            return f"Rich in {', '.join(rich[:3])}"

        if low:
            return f"Lower in {', '.join(low[:3])}"

        return "Balanced nutrient profile"

    # =========================================================
    # EVIDENCE BUILDER
    # =========================================================
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