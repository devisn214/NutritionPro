import numpy as np


class SemanticRanker:

    def __init__(self):
        pass

    # =====================================================
    # COSINE SIMILARITY
    # =====================================================

    def cosine_similarity(
        self,
        vec1,
        vec2
    ):

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        denominator = (
            np.linalg.norm(vec1) *
            np.linalg.norm(vec2)
        )

        if denominator == 0:
            return 0

        similarity = np.dot(
            vec1,
            vec2
        ) / denominator

        return float(similarity)

    # =====================================================
    # SEMANTIC RERANK
    # =====================================================

    def rerank(

        self,

        query_embedding,

        candidate_foods,

        top_k=20

    ):

        ranked = []

        for item in candidate_foods:

            food_embedding = item.get(
                "embedding",
                []
            )

            semantic_score = self.cosine_similarity(

                query_embedding,

                food_embedding
            )

            item["semantic_score"] = round(
                semantic_score,
                4
            )

            ranked.append(item)

        ranked = sorted(

            ranked,

            key=lambda x: x.get(
                "semantic_score",
                0
            ),

            reverse=True
        )

        return ranked[:top_k]

    # =====================================================
    # HYBRID RANKING
    # =====================================================

    def hybrid_rank(

        self,

        semantic_results,

        semantic_weight=0.4,

        symbolic_weight=0.6

    ):

        final_results = []

        for item in semantic_results:

            symbolic_score = float(
                item.get("score", 0)
            )

            semantic_score = float(
                item.get("semantic_score", 0)
            )

            final_score = (

                symbolic_score * symbolic_weight +

                semantic_score * 100 * semantic_weight

            )

            item["hybrid_score"] = round(
                final_score,
                2
            )

            final_results.append(item)

        final_results = sorted(

            final_results,

            key=lambda x: x.get(
                "hybrid_score",
                0
            ),

            reverse=True
        )

        return final_results

    # =====================================================
    # FILTER LOW RELEVANCE
    # =====================================================

    def filter_low_similarity(

        self,

        ranked_results,

        threshold=0.60

    ):

        filtered = []

        for item in ranked_results:

            similarity = item.get(
                "semantic_score",
                0
            )

            if similarity >= threshold:

                filtered.append(item)

        return filtered