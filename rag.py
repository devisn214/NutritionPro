from neo4j import GraphDatabase
from datetime import datetime, timezone

from nutrition_engine.biomarker_interaction import (
    get_biomarker_interactions
)


class NutritionRAG:

    def __init__(
        self,
        uri="bolt://localhost:7687",
        user="neo4j",
        password="neo4jabc"
    ):

        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password)
        )

        self.last_evidence = []

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        if self.driver:
            self.driver.close()

    # =========================================================
    # MAIN RETRIEVAL
    # =========================================================

    def retrieve_context(
        self,
        biomarkers,
        genes,
        biomarker_recs,
        gene_recs,
        diet_preference
    ):

        self.last_evidence = []

        increase_ids = set()
        decrease_ids = set()

        # =====================================================
        # BIOMARKER PROCESSING
        # =====================================================

        for b in biomarker_recs or []:

            nutrient_ids = str(
                b.get("nutrient_id", "")
            ).upper().split()

            direction = str(
                b.get("direction", "")
            ).lower()

            for nid in nutrient_ids:

                nid = nid.strip()

                if not nid:
                    continue

                if direction in [
                    "increase",
                    "maintain",
                    "support",
                    "monitor"
                ]:

                    increase_ids.add(nid)

                    self.last_evidence.append(

                        self._build_evidence(
                            "biomarker",
                            b.get("name"),
                            nid,
                            b.get("target_nutrient", nid),
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
                            b.get("target_nutrient", nid),
                            "high",
                            "decrease"
                        )
                    )

        # =====================================================
        # GENE PROCESSING
        # =====================================================

        for g in gene_recs or []:

            nutrient_ids = str(
                g.get("nutrient_id", "")
            ).upper().split()

            direction = str(
                g.get("direction", "")
            ).lower()

            gene_name = str(
                g.get("gene", "")
            )

            rsid = str(
                g.get("rsid", "")
            )

            genotype = str(
                g.get("genotype", "")
            )

            for nid in nutrient_ids:

                nid = nid.strip()

                if not nid:
                    continue

                if direction in [
                    "increase",
                    "maintain",
                    "support",
                    "monitor"
                ]:

                    increase_ids.add(nid)

                    self.last_evidence.append(

                        self._build_evidence(
                            "gene",
                            f"{gene_name} ({rsid} - {genotype})",
                            nid,
                            g.get("nutrient_name", nid),
                            "genetic",
                            direction
                        )
                    )

                elif direction == "decrease":

                    decrease_ids.add(nid)

                    self.last_evidence.append(

                        self._build_evidence(
                            "gene",
                            f"{gene_name} ({rsid} - {genotype})",
                            nid,
                            g.get("nutrient_name", nid),
                            "sensitivity",
                            "decrease"
                        )
                    )

        # =====================================================
        # INTERACTION ENGINE
        # =====================================================

        interaction_result = get_biomarker_interactions(
            biomarkers
        )

        increase_ids.update(
            interaction_result.get(
                "increase",
                set()
            )
        )

        decrease_ids.update(
            interaction_result.get(
                "decrease",
                set()
            )
        )

        for note in interaction_result.get(
            "notes",
            []
        ):

            self.last_evidence.append({

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "source": "interaction",

                "trigger": "multi-biomarker",

                "nutrient_id": "",

                "status": "combined",

                "action": note,

                "logic_path": note
            })

        # =====================================================
        # CONFLICT RESOLUTION
        # =====================================================

        overlap = (
            increase_ids
            & decrease_ids
        )

        increase_ids = (
            increase_ids - overlap
        )

        decrease_ids = (
            decrease_ids - overlap
        )

        # =====================================================
        # CATEGORY RULES
        # =====================================================

        reward_categories, penalty_categories = \
            self._get_category_rules(
                biomarkers
            )

        # =====================================================
        # MAIN QUERY
        # =====================================================

        with self.driver.session() as session:

            query = """

            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)

            WHERE NOT toLower(f.category) IN [
                'spice',
                'masala',
                'condiment',
                'seasoning'
            ]

            AND (($diet_pref = 'vegan'AND f.diet_type = 'Vegan')OR($diet_pref = 'vegetarian'AND f.diet_type IN ['Vegan','Vegetarian'])OR($diet_pref = 'non-vegetarian'))

            WITH f, n,
                 coalesce(toFloat(r.amount),0)
                 AS amount

            WITH f,

                 collect({

                    id: n.id,
                    name: n.name,
                    amount: amount

                 }) AS nutrient_data,

                 SUM(

                    CASE

                        WHEN n.id IN $increase_ids

                            THEN log(amount + 1) * 3

                        WHEN n.id IN $decrease_ids

                            THEN -4 * log(amount + 1)

                        WHEN n.id = 'N025'

                            THEN -5 * log(amount + 1)

                        WHEN n.id = 'N030'

                            THEN -4 * log(amount + 1)

                        WHEN n.id = 'N006'

                            THEN -3 * log(amount + 1)

                        ELSE 0

                    END

                 ) AS nutrient_score,

                 CASE

                    WHEN toLower(f.category)
                         IN $reward_categories

                        THEN 18

                    ELSE 0

                 END +

                 CASE

                    WHEN toLower(f.category)
                         IN $penalty_categories

                        THEN -25

                    ELSE 0

                 END AS category_score

            WITH f,
                 nutrient_data,

                 (nutrient_score + category_score)
                 AS total_score

            RETURN

                f.id AS food_id,
                f.name AS food,
                f.category AS category,

                nutrient_data,

                total_score

            ORDER BY total_score DESC

            LIMIT 60
            """

            result = session.run(

                query,

                {

                    "diet_pref":
                        (
                            diet_preference
                            or "vegetarian"
                        ).lower(),

                    "increase_ids":
                        list(increase_ids),

                    "decrease_ids":
                        list(decrease_ids),

                    "reward_categories":
                        reward_categories,

                    "penalty_categories":
                        penalty_categories
                }
            )

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

                nutrients = row.get(
                    "nutrient_data"
                ) or []

                score = round(
                    float(
                        row.get(
                            "total_score",
                            0
                        )
                    ),
                    2
                )

                # =============================================
                # FOOD RISK PENALTIES
                # =============================================

                risk_penalty = 0

                for n in nutrients:

                    nid = str(
                        n.get("id", "")
                    ).upper()

                    amt = float(
                        n.get("amount", 0)
                        or 0
                    )

                    # Saturated Fat

                    if nid == "N025":
                        risk_penalty -= amt * 5

                    # Glycemic Load

                    if nid == "N030":
                        risk_penalty -= amt * 3

                    # Sodium

                    if nid == "N006":
                        risk_penalty -= amt * 2

                score += risk_penalty

                # =============================================
                # FOOD CATEGORY DIVERSITY
                # =============================================

                detected_category = "other"

                if any(x in food_lower for x in [
                    "beef",
                    "mutton",
                    "pork",
                    "duck",
                    "goat"
                ]):

                    detected_category = "red_meat"

                elif any(x in food_lower for x in [
                    "fish",
                    "eel",
                    "sardine",
                    "tuna",
                    "mackerel",
                    "salmon",
                    "trevally"
                ]):

                    detected_category = "fish"

                elif any(x in food_lower for x in [
                    "spinach",
                    "moringa",
                    "lettuce",
                    "leaf",
                    "mint"
                ]):

                    detected_category = "leaf"

                elif any(x in food_lower for x in [
                    "seed",
                    "almond",
                    "walnut",
                    "sesame"
                ]):

                    detected_category = "seed"

                elif any(x in food_lower for x in [
                    "dal",
                    "bean",
                    "legume",
                    "peas"
                ]):

                    detected_category = "legume"

                category_counter[
                    detected_category
                ] = category_counter.get(
                    detected_category,
                    0
                ) + 1

                if category_counter[
                    detected_category
                ] > 3:

                    score -= 12

                # =============================================
                # HDL SAFETY
                # =============================================

                biomarker_names = [

                    str(b.get("name", "")).lower()

                    for b in biomarkers
                ]

                if "hdl cholesterol" in biomarker_names:

                    if detected_category == "red_meat":
                        score -= 25

                # =============================================
                # FINAL RESULT
                # =============================================

                balanced_results.append({

                    "food_id": row.get("food_id"),

                    "food": food,

                    "score": round(score, 2),

                    "nutrients": nutrients,

                    "reason": self._generate_reason_for_target(

                        nutrients,

                        increase_ids,

                        decrease_ids
                    )
                })

        # =====================================================
        # FINAL SORT
        # =====================================================

        balanced_results = sorted(

            balanced_results,

            key=lambda x: x.get("score", 0),

            reverse=True
        )

        return balanced_results[:20]

    # =========================================================
    # CATEGORY RULES
    # =========================================================

    def _get_category_rules(self, biomarkers):

        reward = set()
        penalty = set()

        status = {}

        for b in biomarkers or []:

            name = str(
                b.get("name", "")
            ).strip().lower()

            val = str(
                b.get("status", "")
            ).strip().lower()

            status[name] = val

        # =====================================================
        # CARDIOVASCULAR
        # =====================================================

        if status.get("ldl cholesterol") == "high":

            penalty.update([
                "oil",
                "dairy",
                "meat",
                "sweet"
            ])

            reward.update([
                "fish",
                "leaf",
                "legume",
                "grain",
                "nut",
                "seed"
            ])

        if status.get("hdl cholesterol") == "low":
            penalty.update([
                "sweet",
                "grain",
                "oil"
            ])

            reward.update([
                "fish",
                "nut",
                "seed",
                "leaf",
                "legume"
            ])

        if status.get("hdl cholesterol") == "high":

            penalty.update([
                "red meat",
                "processed meat",
                "fried",
                "oil"
            ])

            reward.update([
                "fish",
                "leaf",
                "vegetable",
                "legume"
            ])

        if status.get("total cholesterol") == "high":
            penalty.update([
                "oil",
                "dairy",
                "meat",
                "sweet"
            ])

            reward.update([
                "fish",
                "leaf",
                "legume"
            ])

        if status.get("triglycerides") == "high":

            penalty.update([
                "sweet",
                "grain",
                "tuber",
                "oil"
            ])

            reward.update([
                "fish",
                "leaf",
                "veg",
                "legume"
            ])

        if status.get("hba1c") == "high":

            penalty.update([
                "sweet",
                "grain",
                "tuber"
            ])

            reward.update([
                "leaf",
                "veg",
                "legume",
                "fish",
                "egg"
            ])

        if status.get("fasting glucose") == "high":
            penalty.update([
                "sweet",
                "grain",
                "fruit",
                "tuber"
            ])

            reward.update([
                "leaf",
                "veg",
                "legume",
                "fish",
                "egg"
            ])

        if status.get("uric acid") == "high":
            penalty.update([
                "meat",
                "seafood",
                "sweet"
            ])

            reward.update([
                "veg",
                "fruit",
                "dairy",
                "drink"
            ])

        if status.get("serum sodium") == "high":
            penalty.update([
                "seafood",
                "dairy",
                "meat",
                "sweet"
            ])

            reward.update([
                "fruit",
                "veg",
                "drink",
                "leaf"
            ])

        if status.get("thyroid stimulating hormone (tsh)") == "high":

            reward.update([
                "seafood",
                "seed",
                "vegetable"
            ])

        return list(reward), list(penalty)

    # =========================================================
    # MACRO FALLBACK
    # =========================================================

    def _macro_based_retrieval(
        self,
        diet_preference,
        reward_categories,
        penalty_categories
    ):

        with self.driver.session() as session:

            query = """

            MATCH (f:Food)-[r:CONTAINS]->(n:Nutrient)

            WHERE n.name IN [
                'Net Protein',
                'Total Carbohydrates',
                'Saturated Fat'
            ]

            AND (($diet_pref = 'vegan'AND f.diet_type = 'Vegan')OR($diet_pref = 'vegetarian'AND f.diet_type IN ['Vegan','Vegetarian'])OR($diet_pref = 'non-vegetarian'))

            WITH f,

            collect({

                id:n.id,

                name:n.name,

                amount:coalesce(
                    toFloat(r.amount),
                    0
                )

            }) AS nutrient_data,

            SUM(

                CASE

                    WHEN n.name = 'Net Protein'

                        THEN coalesce(
                            toFloat(r.amount),
                            0
                        ) * 2.5

                    WHEN n.name = 'Total Carbohydrates'

                        THEN coalesce(
                            toFloat(r.amount),
                            0
                        ) * 1.2

                    WHEN n.name = 'Saturated Fat'

                        THEN coalesce(
                            toFloat(r.amount),
                            0
                        ) * -3

                    ELSE 0

                END

            ) AS macro_score

            WITH f,
                 nutrient_data,

                 (
                    macro_score +

                    CASE
                        WHEN toLower(f.category)
                             IN $reward_categories

                        THEN 18

                        ELSE 0
                    END +

                    CASE
                        WHEN toLower(f.category)
                             IN $penalty_categories

                        THEN -25

                        ELSE 0
                    END

                 ) AS score

            RETURN

                f.id AS food_id,

                f.name AS food,

                nutrient_data,

                score

            ORDER BY score DESC

            LIMIT 20
            """

            result = session.run(

                query,

                {

                    "diet_pref": (
                        diet_preference
                        or "vegetarian"
                    ).lower(),

                    "reward_categories": reward_categories,

                    "penalty_categories": penalty_categories
                }
            )

            return [

                {

                    "food_id": row.get("food_id"),

                    "food": row.get("food"),

                    "score": row.get("score"),

                    "nutrients": row.get(
                        "nutrient_data",
                        []
                    ),

                    "reason": "Macro-balanced food"
                }

                for row in result
            ]

    # =========================================================
    # EXPLANATION
    # =========================================================

    def _generate_reason_for_target(
        self,
        nutrient_data,
        increase_ids,
        decrease_ids
    ):

        rich = []
        low = []

        for n in nutrient_data:

            nid = str(
                n.get("id", "")
            ).upper()

            name = n.get("name", "")

            if nid in increase_ids:
                rich.append(name)

            if nid in decrease_ids:
                low.append(name)

        rich = list(dict.fromkeys(rich))
        low = list(dict.fromkeys(low))

        if rich and low:

            return (
                f"Rich in {', '.join(rich[:3])} | "
                f"Lower in {', '.join(low[:2])}"
            )

        if rich:
            return f"Rich in {', '.join(rich[:3])}"

        if low:
            return f"Lower in {', '.join(low[:2])}"

        return "Balanced nutrient profile"

    # =========================================================
    # EVIDENCE
    # =========================================================

    def _build_evidence(
        self,
        source,
        name,
        n_id,
        nutrient_name,
        status,
        action
    ):

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "trigger": name,
            "nutrient_id": n_id,
            "nutrient_name": nutrient_name,
            "status": status,
            "action": action,
            "logic_path":f"{source.upper()} ({name}) → {nutrient_name} → {action}"
        }