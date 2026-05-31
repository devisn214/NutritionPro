
from neo4j import GraphDatabase
from datetime import datetime, timezone

from new.vector_store import SemanticRetriever
from new.adaptive_engine import AdaptiveEngine


class NutritionRAG:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4jabc"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.last_evidence = []
        self.vector_store = SemanticRetriever()
        self.adaptive_engine = AdaptiveEngine()

    # =========================================================
    # CLOSE
    # =========================================================
    def close(self):
        if self.driver:
            self.driver.close()

    # =========================================================
    # MAIN RETRIEVAL
    # =========================================================
    def retrieve_context(self, biomarkers, genes, biomarker_recs, gene_recs, diet_preference, user_id):
        self.last_evidence = []
        increase_ids = set()
        decrease_ids = set()
        increase_names = []
        decrease_names = []
        increase_weights = {}
        decrease_weights = {}

        # =====================================================
        # BIOMARKER PROCESSING
        # =====================================================
        for b in biomarker_recs or []:
            nutrient_ids = str(b.get("nutrient_id", "")).upper().split()
            direction = str(b.get("direction", "")).lower()

            biomarker_name = str(b.get("biomarker") or b.get("name") or "Unknown Biomarker")
            if biomarker_name.startswith("Gene-"):
                continue

            nutrient_name = str(b.get("target_nutrient") or b.get("nutrient_name") or "Unknown Nutrient")

            for nid in nutrient_ids:
                nid = nid.strip()
                if not nid:
                    continue

                if direction in ["increase"]:
                    increase_ids.add(nid)
                    increase_weights[nid] = max(increase_weights.get(nid, 0), 5)
                    increase_names.append(nutrient_name)
                    self.last_evidence.append(
                        self._build_evidence(
                            "biomarker",
                            biomarker_name,
                            nid,
                            nutrient_name,
                            b.get("status", "low"),
                            direction
                        )
                    )

                elif direction in ["maintain"]:
                    increase_ids.add(nid)
                    increase_weights[nid] = max(increase_weights.get(nid, 0), 3)
                    increase_names.append(nutrient_name)
                    self.last_evidence.append(
                        self._build_evidence(
                            "biomarker",
                            biomarker_name,
                            nid,
                            nutrient_name,
                            b.get("status", "maintain"),
                            direction
                        )
                    )

                elif direction in ["decrease"]:
                    decrease_ids.add(nid)
                    decrease_weights[nid] = max(decrease_weights.get(nid, 0), 5)
                    decrease_names.append(nutrient_name)
                    self.last_evidence.append(
                        self._build_evidence(
                            "biomarker",
                            biomarker_name,
                            nid,
                            nutrient_name,
                            b.get("status", "high"),
                            direction
                        )
                    )

        # =====================================================
        # GENE PROCESSING
        # =====================================================
        for g in gene_recs or []:
            nutrient_ids = str(g.get("nutrient_id", "")).upper().split()
            direction = str(g.get("direction", "")).lower()
            gene_name = str(g.get("gene", ""))
            rsid = str(g.get("rsid", ""))
            genotype = str(g.get("genotype", ""))
            nutrient_name = str(g.get("nutrient_name") or "Unknown Nutrient")

            for nid in nutrient_ids:
                nid = nid.strip()
                if not nid:
                    continue

                if direction == "increase":
                    increase_ids.add(nid)
                    increase_weights[nid] = max(increase_weights.get(nid, 0), 5)
                    increase_names.append(nutrient_name)
                    self.last_evidence.append(
                        self._build_evidence(
                            "gene",
                            f"{gene_name} ({rsid} - {genotype})",
                            nid,
                            nutrient_name,
                            "genetic",
                            direction
                        )
                    )

                elif direction in ["maintain", "monitor"]:
                    increase_ids.add(nid)
                    increase_weights[nid] = max(increase_weights.get(nid, 0), 3)
                    increase_names.append(nutrient_name)
                    self.last_evidence.append(
                        self._build_evidence(
                            "gene",
                            f"{gene_name} ({rsid} - {genotype})",
                            nid,
                            nutrient_name,
                            "genetic",
                            direction
                        )
                    )

                elif direction == "decrease":
                    decrease_ids.add(nid)
                    decrease_weights[nid] = max(decrease_weights.get(nid, 0), 5)
                    decrease_names.append(nutrient_name)
                    self.last_evidence.append(
                        self._build_evidence(
                            "gene",
                            f"{gene_name} ({rsid} - {genotype})",
                            nid,
                            nutrient_name,
                            "sensitivity",
                            direction
                        )
                    )

        # =====================================================
        # CONFLICT RESOLUTION
        # =====================================================
        overlap = increase_ids & decrease_ids
        increase_ids = increase_ids - overlap
        decrease_ids = decrease_ids - overlap
        
        for nid in overlap:
            increase_weights.pop(nid, None)
            decrease_weights.pop(nid, None)

        # =====================================================
        # SEMANTIC QUERY
        # =====================================================
        semantic_query = self.vector_store.build_query(
            increase_nutrients=increase_names,
            decrease_nutrients=decrease_names,
            diet_preference=diet_preference,
            biomarkers=[str(x.get("name", "")) for x in biomarkers],
            genes=[str(x.get("gene", "")) for x in genes]
        )

        semantic_scores = self.vector_store.retrieve_as_score_map(
            semantic_query,
            top_k=80
        )

        # =====================================================
        # MAIN QUERY
        # =====================================================
        with self.driver.session() as session:
            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)
            WHERE NOT toLower(f.category) IN ['spice', 'masala', 'condiment', 'seasoning']
            AND (
                ($diet_pref = 'vegan' AND f.diet_type = 'Vegan')
                OR ($diet_pref = 'vegetarian' AND f.diet_type IN ['Vegan','Vegetarian'])
                OR ($diet_pref = 'non-vegetarian')
            )
            WITH f, n, coalesce(toFloat(r.amount), 0) AS amount
            WITH f,
                 collect({
                    id: n.id,
                    name: n.name,
                    amount: amount
                 }) AS nutrient_data,
                 SUM(
                    CASE
                        WHEN n.id IN $increase_ids THEN log(amount + 1) * coalesce($increase_weights[n.id], 1)
                        WHEN n.id IN $decrease_ids THEN -1 * log(amount + 1) * coalesce($decrease_weights[n.id], 5)
                        ELSE 0
                    END
                 ) AS total_score
            RETURN
                f.id AS food_id,
                f.name AS food,
                f.category AS category,
                nutrient_data,
                total_score
            ORDER BY total_score DESC
            LIMIT 80
            """

            result = session.run(query, {
                "diet_pref": (diet_preference or "vegetarian").lower(),
                "increase_ids": list(increase_ids),
                "decrease_ids": list(decrease_ids),
                "increase_weights": increase_weights,
                "decrease_weights": decrease_weights
            })

            balanced_results = []
            category_counter = {}
            used_foods = set()

            for row in result:
                food = row.get("food")
                if not food:
                    continue

                food_lower = food.lower()
                if food_lower in used_foods:
                    continue

                used_foods.add(food_lower)
                nutrients = row.get("nutrient_data") or []
                score = round(float(row.get("total_score", 0)), 2)

                # =================================================
                # SEMANTIC SCORE
                # =================================================
                semantic_score = semantic_scores.get(food_lower, 0)
                score += semantic_score * 30

                # =================================================
                # ADAPTIVE SCORE
                # =================================================
                adaptive_score = self.adaptive_engine.get_adaptive_score(user_id, food)
                score += adaptive_score

                # =================================================
                # FOOD CATEGORY DIVERSITY
                # =================================================
                detected_category = "other"

                if any(x in food_lower for x in ["fish", "salmon", "tuna", "mackerel", "sardine"]):
                    detected_category = "fish"
                elif any(x in food_lower for x in ["spinach", "moringa", "leaf"]):
                    detected_category = "leaf"
                elif any(x in food_lower for x in ["seed", "almond", "sesame"]):
                    detected_category = "seed"
                elif any(x in food_lower for x in ["dal", "bean", "legume"]):
                    detected_category = "legume"

                category_counter[detected_category] = category_counter.get(detected_category, 0) + 1

                if category_counter[detected_category] > 3:
                    score -= 10

                # =================================================
                # FINAL RESULT
                # =================================================
                balanced_results.append({
                    "food_id": row.get("food_id"),
                    "food": food,
                    "score": round(score, 2),
                    "semantic_score": round(semantic_score, 4),
                    "adaptive_score": round(adaptive_score, 2),
                    "nutrients": nutrients,
                    "reason": self._generate_reason_for_target(nutrients, increase_ids, decrease_ids),
                    "semantic_reason": "Retrieved using semantic embedding similarity and biomarker-gene nutritional reasoning"
                })

        # =====================================================
        # FINAL SORT
        # =====================================================
        balanced_results = sorted(balanced_results, key=lambda x: x.get("score", 0), reverse=True)
        return balanced_results[:20]

    # =========================================================
    # MACRO FALLBACK
    # =========================================================
    def _macro_based_retrieval(self, diet_preference):
        with self.driver.session() as session:
            query = """
            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)
            WHERE n.name IN ['Net Protein', 'Total Carbohydrates', 'Saturated Fat']
            AND (
                ($diet_pref = 'vegan' AND f.diet_type = 'Vegan')
                OR ($diet_pref = 'vegetarian' AND f.diet_type IN ['Vegan','Vegetarian'])
                OR ($diet_pref = 'non-vegetarian')
            )
            WITH f,
                 collect({
                    id: n.id,
                    name: n.name,
                    amount: coalesce(toFloat(r.amount), 0)
                 }) AS nutrient_data,
                 SUM(
                    CASE
                        WHEN n.name = 'Net Protein' THEN coalesce(toFloat(r.amount), 0) * 2.5
                        WHEN n.name = 'Total Carbohydrates' THEN coalesce(toFloat(r.amount), 0) * 1.2
                        WHEN n.name = 'Saturated Fat' THEN coalesce(toFloat(r.amount), 0) * -3
                        ELSE 0
                    END
                 ) AS macro_score
            WITH f, nutrient_data, macro_score AS score
            RETURN f.id AS food_id, f.name AS food, nutrient_data, score
            ORDER BY score DESC
            LIMIT 20
            """

            result = session.run(query, {
                "diet_pref": (diet_preference or "vegetarian").lower()
            })

            return [
                {
                    "food_id": row.get("food_id"),
                    "food": row.get("food"),
                    "score": row.get("score"),
                    "nutrients": row.get("nutrient_data", []),
                    "reason": "Macro-balanced food"
                }
                for row in result
            ]

    # =========================================================
    # EXPLANATION
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

        # Remove duplicates while preserving order
        rich = list(dict.fromkeys(rich))
        low = list(dict.fromkeys(low))

        if rich and low:
            return f"Rich in {', '.join(rich[:3])} | Lower in {', '.join(low[:2])}"
        if rich:
            return f"Rich in {', '.join(rich[:3])}"
        if low:
            return f"Lower in {', '.join(low[:2])}"

        return "Balanced nutrient profile"

    # =========================================================
    # EVIDENCE
    # =========================================================
    def _build_evidence(self, source, name, n_id, nutrient_name, status, action):
        if source == "biomarker":
            logic_path = (
                f"{name.title()} is outside the healthy reference range "
                f"({status}). Nutritional evidence indicates that "
                f"{nutrient_name} may help support this biomarker. "
                f"The recommendation system therefore prioritizes foods that "
                f"{action} {nutrient_name.lower()} intake."
            )
        else:
            logic_path = (
                f"The detected genetic variant {name} influences nutritional "
                f"requirements related to {nutrient_name}. "
                f"To better align the meal plan with the user's genomic profile, "
                f"foods that {action} {nutrient_name.lower()} intake are prioritized."
            )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "trigger": name,
            "nutrient_id": n_id,
            "nutrient_name": nutrient_name,
            "status": status,
            "action": action,
            "logic_path": logic_path
        }

