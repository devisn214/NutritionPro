import json
import numpy as np

from sentence_transformers import SentenceTransformer

from new.semantic_ranker import SemanticRanker


class SemanticRetriever:

    def __init__(

        self,

        embedding_path="data/food_embeddings.json",

        model_name="pritamdeka/S-PubMedBert-MS-MARCO"

    ):

        self.embedding_path = embedding_path

        self.model = SentenceTransformer(
            model_name
        )

        self.ranker = SemanticRanker()

        self.food_data = self.load_embeddings()

    # =====================================================
    # LOAD EMBEDDINGS
    # =====================================================

    def load_embeddings(self):

        with open(self.embedding_path, "r", encoding="utf-8") as f:

            data = json.load(f)

        cleaned = []

        for item in data:

            cleaned.append({

                "food_id": item.get("food_id"),

                "food_name": item.get("food_name"),

                "description": item.get("description"),

                "embedding": np.array(
                    item.get("embedding", []),
                    dtype=np.float32
                )
            })

        return cleaned

    # =====================================================
    # ENCODE QUERY
    # =====================================================

    def encode_query(

        self,

        query

    ):

        embedding = self.model.encode(
            query
        )

        return np.array(
            embedding,
            dtype=np.float32
        )

    # =====================================================
    # RETRIEVE
    # =====================================================

    def retrieve(

        self,

        query,

        top_k=20,

        similarity_threshold=0.20

    ):

        query_embedding = self.encode_query(
            query
        )

        candidates = []

        for item in self.food_data:

            candidates.append({

                "food_id": item["food_id"],

                "food_name": item["food_name"],

                "description": item["description"],

                "embedding": item["embedding"]
            })

        ranked = self.ranker.rerank(

            query_embedding,

            candidates,

            top_k=top_k * 3
        )

        ranked = self.ranker.filter_low_similarity(

            ranked,

            threshold=similarity_threshold
        )

        final_results = []

        for item in ranked[:top_k]:

            final_results.append({

                "food_id": item["food_id"],

                "food_name": item["food_name"],

                "description": item["description"],

                "semantic_score": round(
                    item.get(
                        "semantic_score",
                        0
                    ),
                    4
                )
            })

        return final_results

    # =====================================================
    # RETRIEVE SCORE MAP
    # =====================================================

    def retrieve_as_score_map(

        self,

        query,

        top_k=50

    ):

        results = self.retrieve(

            query=query,

            top_k=top_k
        )

        score_map = {}

        for item in results:

            score_map[
                item["food_name"].lower()
            ] = item["semantic_score"]

        return score_map

    # =====================================================
    # BUILD QUERY
    # =====================================================

    def build_query(

        self,

        increase_nutrients,

        decrease_nutrients,

        diet_preference,

        biomarkers=[],

        genes=[]

    ):

        increase_text = ", ".join(
            increase_nutrients
        )

        decrease_text = ", ".join(
            decrease_nutrients
        )

        biomarker_text = ", ".join(
            biomarkers
        )

        gene_text = ", ".join(
            genes
        )

        query = f"""

        Personalized nutrition recommendation query.

        Diet preference:
        {diet_preference}

        Increase nutrients:
        {increase_text}

        Reduce nutrients:
        {decrease_text}

        Biomarker conditions:
        {biomarker_text}

        Genetic factors:
        {gene_text}

        Recommend foods that best support these nutritional requirements.

        """

        return query.strip()