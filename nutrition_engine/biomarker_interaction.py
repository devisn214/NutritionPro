# biomarker_interactions.py
# ------------------------------------------------------------
# CONTRADICTION RULES ONLY
# For difficult mixed biomarker cases:
# LDL, HDL, HbA1c, Fasting Glucose, Sodium,
# B12, Potassium, Vitamin D
#
# Existing logic already handles:
# low biomarker  -> increase nutrient
# high biomarker -> decrease nutrient
#
# This file handles contradictions / balancing only.
# ------------------------------------------------------------


def get_biomarker_interactions(biomarkers):

    result = {
        "increase": set(),
        "decrease": set(),
        "notes": []
    }

    if not biomarkers:
        return result

    status = {}

    for b in biomarkers:
        name = str(b.get("name", "")).strip().lower()
        val = str(b.get("status", "")).strip().lower()
        status[name] = val

    # ==========================================================
    # LIPIDS
    # ==========================================================

    # LDL HIGH + HDL LOW
    if status.get("ldl cholesterol") == "high" and status.get("hdl cholesterol") == "low":
        result["increase"].update(["N026", "N029", "N003"])
        result["decrease"].update(["N024", "N025"])
        result["notes"].append(
            "LDL high + HDL low: use omega-3, magnesium, fiber. Avoid saturated fat."
        )

    # LDL HIGH + HDL HIGH
    if status.get("ldl cholesterol") == "high" and status.get("hdl cholesterol") == "high":
        result["increase"].update(["N026", "N029"])
        result["decrease"].update(["N025"])
        result["notes"].append(
            "HDL is protective, but LDL remains high. Reduce saturated fat."
        )

    # LDL LOW + HDL LOW
    if status.get("ldl cholesterol") == "low" and status.get("hdl cholesterol") == "low":
        result["increase"].update(["N027", "N026"])
        result["notes"].append(
            "Low LDL + low HDL: improve healthy fats and protein quality."
        )

    # ==========================================================
    # GLUCOSE
    # ==========================================================

    # HbA1c HIGH + Fasting Glucose HIGH
    if status.get("hba1c") == "high" and status.get("fasting glucose") == "high":
        result["increase"].update(["N029", "N003"])
        result["decrease"].update(["N028", "N030"])
        result["notes"].append(
            "Chronic and fasting glucose high: strong low-glycemic strategy."
        )

    # HbA1c HIGH + Fasting Glucose NORMAL
    if status.get("hba1c") == "high" and status.get("fasting glucose") == "normal":
        result["increase"].update(["N029"])
        result["decrease"].update(["N028", "N030"])
        result["notes"].append(
            "Possible post-meal glucose spikes. Reduce refined carbs."
        )

    # HbA1c NORMAL + Fasting Glucose HIGH
    if status.get("hba1c") == "normal" and status.get("fasting glucose") == "high":
        result["increase"].update(["N003", "N029"])
        result["decrease"].update(["N030"])
        result["notes"].append(
            "Possible early insulin resistance or stress glucose."
        )

    # HbA1c LOW + Fasting Glucose LOW
    if status.get("hba1c") == "low" and status.get("fasting glucose") == "low":
        result["increase"].update(["N028", "N027"])
        result["notes"].append(
            "Low glucose pattern: ensure regular balanced meals."
        )

    # ==========================================================
    # SODIUM / POTASSIUM
    # ==========================================================

    # Sodium HIGH + Potassium LOW
    if status.get("serum sodium") == "high" and status.get("serum potassium") == "low":
        result["increase"].update(["N005", "N003"])
        result["decrease"].update(["N006"])
        result["notes"].append(
            "High sodium + low potassium: prioritize potassium-rich foods."
        )

    # Sodium LOW + Potassium HIGH
    if status.get("serum sodium") == "low" and status.get("serum potassium") == "high":
        result["decrease"].update(["N005"])
        result["notes"].append(
            "Low sodium + high potassium: avoid aggressive potassium loading."
        )

    # Sodium HIGH + Potassium HIGH
    if status.get("serum sodium") == "high" and status.get("serum potassium") == "high":
        result["decrease"].update(["N006"])
        result["notes"].append(
            "Electrolyte imbalance: reduce sodium, monitor potassium sources."
        )

    # ==========================================================
    # B12
    # ==========================================================

    # B12 LOW + HbA1c HIGH
    if status.get("serum vitamin b12") == "low" and status.get("hba1c") == "high":
        result["increase"].update(["N012", "N027"])
        result["decrease"].update(["N028"])
        result["notes"].append(
            "Low B12 + high HbA1c: improve B12 while reducing refined carbs."
        )

    # B12 LOW + Vitamin D LOW
    if status.get("serum vitamin b12") == "low" and status.get("25-hydroxy vitamin d") == "low":
        result["increase"].update(["N012", "N011", "N027"])
        result["notes"].append(
            "Low B12 + low Vitamin D: prioritize nutrient-dense protein foods."
        )

    # B12 HIGH + LDL HIGH
    if status.get("serum vitamin b12") == "high" and status.get("ldl cholesterol") == "high":
        result["decrease"].update(["N025"])
        result["notes"].append(
            "If B12 from animal-heavy diet, choose leaner lower saturated-fat sources."
        )

    # ==========================================================
    # VITAMIN D
    # ==========================================================

    # Vitamin D LOW + LDL HIGH
    if status.get("25-hydroxy vitamin d") == "low" and status.get("ldl cholesterol") == "high":
        result["increase"].update(["N011", "N026"])
        result["decrease"].update(["N025"])
        result["notes"].append(
            "Use low-saturated-fat Vitamin D sources."
        )

    # Vitamin D LOW + HbA1c HIGH
    if status.get("25-hydroxy vitamin d") == "low" and status.get("hba1c") == "high":
        result["increase"].update(["N011", "N003"])
        result["decrease"].update(["N028"])
        result["notes"].append(
            "Low Vitamin D + high HbA1c: improve D and glycemic control."
        )

    # Vitamin D HIGH + Calcium HIGH
    if status.get("25-hydroxy vitamin d") == "high" and status.get("serum calcium") == "high":
        result["decrease"].update(["N011", "N002"])
        result["notes"].append(
            "High Vitamin D + calcium: avoid excess fortified sources."
        )

    return result
