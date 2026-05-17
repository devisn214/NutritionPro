class ExplainabilityEngine:

    def __init__(self):
        pass

    # =====================================================
    # BUILD FOOD TRACE
    # =====================================================

    def build_trace(

        self,

        food_name,

        matched_nutrients=[],

        biomarker_reasons=[],

        gene_reasons=[],

        semantic_score=0,

        adaptive_score=0,

        confidence_score=0

    ):

        trace = []

        # =================================================
        # BIOMARKER TRACE
        # =================================================

        for item in biomarker_reasons:

            biomarker = item.get(
                "biomarker",
                "Unknown Biomarker"
            )

            status = item.get(
                "status",
                "unknown"
            )

            nutrient = item.get(
                "target_nutrient",
                "Unknown Nutrient"
            )

            direction = item.get(
                "direction",
                "support"
            )

            trace.append(

                f"Biomarker '{biomarker}' was detected as '{status}', requiring '{direction}' support for '{nutrient}'."

            )

        # =================================================
        # GENE TRACE
        # =================================================

        for item in gene_reasons:

            gene = item.get(
                "gene",
                "Unknown Gene"
            )

            rsid = item.get(
                "rsid",
                "Unknown RSID"
            )

            genotype = item.get(
                "genotype",
                "Unknown Genotype"
            )

            nutrient = item.get(
                "nutrient_name",
                "Unknown Nutrient"
            )

            trace.append(

                f"Gene '{gene}' with variant '{rsid}' and genotype '{genotype}' influenced nutrient recommendation for '{nutrient}'."

            )

        # =================================================
        # NUTRIENT MATCH TRACE
        # =================================================

        if matched_nutrients:

            nutrient_text = ", ".join(
                matched_nutrients
            )

            trace.append(

                f"The food '{food_name}' matched important nutritional targets including: {nutrient_text}."

            )

        # =================================================
        # SEMANTIC TRACE
        # =================================================

        trace.append(

            f"Semantic retrieval similarity score for '{food_name}' was {round(semantic_score, 2)}."

        )

        # =================================================
        # ADAPTIVE TRACE
        # =================================================

        if adaptive_score > 0:

            trace.append(

                f"Adaptive learning positively boosted '{food_name}' based on previous user preferences."

            )

        elif adaptive_score < 0:

            trace.append(

                f"Adaptive learning reduced ranking for '{food_name}' due to previous negative feedback."

            )

        else:

            trace.append(

                f"No adaptive preference history was available for '{food_name}'."

            )

        # =================================================
        # CONFIDENCE TRACE
        # =================================================

        trace.append(

            f"The final explainability confidence score for '{food_name}' was {round(confidence_score, 2)}%."

        )

        return trace

    # =====================================================
    # BUILD GLOBAL EXPLANATION
    # =====================================================

    def build_global_explanation(

        self,

        biomarker_recommendations=[],

        gene_recommendations=[],

        retrieved_foods=[],

        confidence_score=0

    ):

        explanation = []

        # =================================================
        # BIOMARKER SUMMARY
        # =================================================

        if biomarker_recommendations:

            explanation.append(

                "Biomarker analysis identified nutrient deficiencies and metabolic imbalances requiring nutritional intervention."

            )

        # =================================================
        # GENE SUMMARY
        # =================================================

        if gene_recommendations:

            explanation.append(

                "Genetic nutrigenomic analysis identified gene-nutrient interactions influencing dietary recommendations."

            )

        # =================================================
        # RETRIEVAL SUMMARY
        # =================================================

        if retrieved_foods:

            food_names = [

                f.get("food", "")

                for f in retrieved_foods
            ]

            food_text = ", ".join(
                food_names[:10]
            )

            explanation.append(

                f"Knowledge graph retrieval and semantic ranking selected foods including: {food_text}."

            )

        # =================================================
        # CONFIDENCE SUMMARY
        # =================================================

        explanation.append(

            f"The overall recommendation confidence score was {round(confidence_score, 2)}%."

        )

        return explanation

    # =====================================================
    # BUILD RETRIEVAL TRACE
    # =====================================================

    def retrieval_pipeline_trace(

        self,

        biomarkers=[],

        genes=[],

        nutrients=[],

        semantic_enabled=True,

        adaptive_enabled=True

    ):

        pipeline = []

        pipeline.append(

            "User biomarkers and genetic variants were analyzed."

        )

        if biomarkers:

            biomarker_text = ", ".join(
                biomarkers
            )

            pipeline.append(

                f"Detected biomarkers: {biomarker_text}."

            )

        if genes:

            gene_text = ", ".join(
                genes
            )

            pipeline.append(

                f"Detected genes: {gene_text}."

            )

        if nutrients:

            nutrient_text = ", ".join(
                nutrients
            )

            pipeline.append(

                f"Nutrient targets identified: {nutrient_text}."

            )

        pipeline.append(

            "Neo4j knowledge graph retrieval was performed to identify biologically relevant foods."

        )

        if semantic_enabled:

            pipeline.append(

                "Semantic vector retrieval and embedding similarity ranking were applied."

            )

        if adaptive_enabled:

            pipeline.append(

                "Adaptive reinforcement learning adjusted rankings using historical user feedback."

            )

        pipeline.append(

            "Confidence scoring and explainability analysis generated the final recommendations."

        )

        return pipeline