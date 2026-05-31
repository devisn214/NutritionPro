import math


def normalize_score(value, max_value=100):

    if value <= 0:
        return 0

    return min(value / max_value, 1.0)


def semantic_confidence(semantic_score):

    return max(0, min(1, semantic_score))


def adaptive_confidence(adaptive_score):

    normalized = (adaptive_score + 20) / 40

    return max(0, min(1, normalized))


def biomarker_coverage_score(
    matched_nutrients,
    increase_ids,
    decrease_ids
):

    target_nutrients = set(
        increase_ids + decrease_ids
    )

    if not target_nutrients:
        return 0

    matched = len(

        set(matched_nutrients).intersection(
            target_nutrients
        )

    )

    return matched / len(target_nutrients)


def diversity_score(matched_nutrients):

    unique_count = len(
        set(matched_nutrients)
    )

    return min(unique_count / 6, 1.0)


def gene_support_score(
    matched_nutrients,
    increase_ids,decrease_ids
):
    target_nutrients = set(
        increase_ids + decrease_ids
    )

    if not target_nutrients:
        return 0

    overlap = len(

        set(matched_nutrients).intersection(
            target_nutrients
        )

    )

    return overlap / len(target_nutrients)


def calculate_confidence(
    matched_nutrients,
    increase_ids,
    decrease_ids,
    semantic_score=0,
    adaptive_score=0
):

    biomarker_score = biomarker_coverage_score(
        matched_nutrients,
        increase_ids,
        decrease_ids
    )

    semantic_component = semantic_confidence(
        semantic_score
    )

    adaptive_component = adaptive_confidence(
        adaptive_score
    )

    diversity_component = diversity_score(
        matched_nutrients
    )

    gene_component = gene_support_score(
        matched_nutrients,
        increase_ids,
        decrease_ids
    )

    final_score = (

        biomarker_score * 0.35 +

        semantic_component * 0.25 +

        gene_component * 0.30 +

        adaptive_component * 0.10

    )

    boosted = math.sqrt(
        max(final_score, 0)
    )

    confidence_percent = round(
        boosted * 100,
        2
    )

    return max(
        0,
        min(100, confidence_percent)
    )


class ConfidenceEngine:

    # =====================================================
    # FOOD CONFIDENCE
    # =====================================================

    def calculate_food_confidence(
        self,
        matched_nutrients,
        increase_ids,
        decrease_ids,
        semantic_score=0,
        adaptive_score=0
    ):

        return calculate_confidence(

            matched_nutrients,

            increase_ids,

            decrease_ids,

            semantic_score,

            adaptive_score
        )

    # =====================================================
    # GENERIC CONFIDENCE
    # =====================================================

    def calculate_confidence(
        self,
        matched_nutrients,
        increase_ids,
        decrease_ids,
        semantic_score=0,
        adaptive_score=0
    ):

        return calculate_confidence(

            matched_nutrients,

            increase_ids,

            decrease_ids,

            semantic_score,

            adaptive_score
        )

    # =====================================================
    # GLOBAL CONFIDENCE
    # =====================================================

    def calculate_global_confidence(
        self,
        rag_context=[],
        biomarker_recommendations=[],
        gene_recommendations=[],
        semantic_scores=[],
        adaptive_scores=[],
        llm_response=""
    ):

        matched_nutrients = []

        increase_ids = []

        decrease_ids = []

        # =================================================
        # RAG NUTRIENTS
        # =================================================

        for item in rag_context:

            for n in item.get(
                "nutrients",
                []
            ):

                nid = str(
                    n.get("id", "")
                ).upper()

                if nid:
                    matched_nutrients.append(nid)

        # =================================================
        # BIOMARKERS
        # =================================================

        for b in biomarker_recommendations:

            nid = str(
                b.get("nutrient_id", "")
            ).upper()

            direction = str(
                b.get("direction", "")
            ).lower()

            if not nid:
                continue

            if direction in [
                "increase",
                "support",
                "maintain",
                "monitor"
            ]:

                increase_ids.append(nid)

            elif direction == "decrease":

                decrease_ids.append(nid)

        # =================================================
        # GENES
        # =================================================

        for g in gene_recommendations:

            nid = str(
                g.get("nutrient_id", "")
            ).upper()

            direction = str(
                g.get("direction", "")
            ).lower()

            if not nid:
                continue

            if direction in [
                "increase",
                "support",
                "maintain",
                "monitor"
            ]:

                increase_ids.append(nid)

            elif direction == "decrease":

                decrease_ids.append(nid)

        # =================================================
        # SEMANTIC SCORE
        # =================================================

        semantic_score = 0

        adaptive_score = 0

        if semantic_scores:

            semantic_score = sum(
                semantic_scores
            ) / len(semantic_scores)

        # =================================================
        # ADAPTIVE SCORE
        # =================================================

        if adaptive_scores:

            adaptive_score = sum(
                adaptive_scores
            ) / len(adaptive_scores)

        # =================================================
        # FINAL CONFIDENCE
        # =================================================

        confidence = self.calculate_confidence(

            matched_nutrients,

            increase_ids,

            decrease_ids,

            semantic_score,

            adaptive_score
        )

        # =================================================
        # BOOST IF LLM WORKED
        # =================================================

        if (
            llm_response and
            "Service Error" not in llm_response
        ):

            confidence += 5

        return min(confidence, 100)