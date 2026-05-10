import re

# ---------------- SYNONYMS ----------------
BIOMARKER_SYNONYMS = {
    # --- IRON & ANEMIA ---
    "Serum Ferritin": ["serum ferritin", "ferritin"],
    "Serum Iron": ["IRON, SERUM","serum iron", "iron, serum"], 
    "Transferrin Saturation (TSAT)": ["transferrin saturation", "tsat", "iron saturation"],
    "Hemoglobin": ["hemoglobin"], 

    # --- BLOOD SUGAR & METABOLIC ---
    "HbA1c": ["hba1c","glycosylated hemoglobin","glycosylated haemoglobin","hb a1c"],
    "Fasting Glucose": ["fasting glucose",  "fasting blood sugar", "glucose fasting", "glucose, fluoride plasma","FBS-FASTING BLOOD SUGAR(GLUCOSE)"],
    "Uric Acid": ["uric acid, serum","uric acid"],

    # --- LIPIDS (CHOLESTEROL) ---
    "Total Cholesterol": ["cholesterol, total", "total cholesterol", "cholestrol-total"], 
    "LDL Cholesterol": ["ldl cholesterol", "cholesterol - ldl", "cholesterol ldl", "bad cholesterol", "ldl"], 
    "HDL Cholesterol": ["hdl cholesterol", "cholesterol hdl", "cholesterol - hdl", "good cholesterol", "hdl"],
    "Triglycerides": ["triglycerides"], 

    # --- KIDNEY FUNCTION ---
    "Blood Urea Nitrogen (BUN)": ["blood urea nitrogen","Blood Urea Nitrogen (BUN)"], 

    # --- LIVER & ENZYMES ---
    "Alkaline Phosphatase (ALP)": ["alkaline phosphatase", "alk phos", "alkaline phosphaqtase","ALK PHOS"],
    "Serum Bilirubin": [ "bilirubin, total", "BILIRUBIN-TOTAL"],


    # --- PROTEINS & INFLAMMATION ---
    "Serum Albumin": ["serum albumin", "albumin", "ALBUMIN"],
    "Total Protein": ["total protein", "protein, total", "TOTAL PROTEIN"],
    "hs-CRP": ["hs-crp", "c-reactive protein", "high sensitivity crp"],
    "ESR": ["erythrocyte sedimentation rate", "sedimentation rate(ESR)"],

    # --- ELECTROLYTES & MINERALS ---
    "Serum Calcium": ["serum calcium", "calcium", "total calcium"],
    "Ionized Calcium": ["ionized calcium"], 
    "Serum Magnesium": ["serum magnesium", "magnesium"],
    "Serum Sodium": ["serum sodium", "sodium"],
    "Serum Potassium": ["serum potassium", "potassium"],
    "Serum Phosphate": ["serum phosphate", "phosphorus"], 
    "Serum Manganese": ["serum manganese", "manganese"],
    "Serum Copper": ["serum copper", "copper"],
    "Serum Selenium": ["serum selenium", "selenium"],

    # --- VITAMINS ---
    "25-Hydroxy Vitamin D": [ "25 hydroxy Vitamin D Total","25-hydroxy vitamin d"],
    "Serum Vitamin B12": ["serum vitamin b12", "cobalamin","VITAMIN B12"],
    "Serum Folate": ["serum folate", "vitamin b9"],
    "Serum Retinol": ["serum retinol", "vitamin a"],
    "Plasma Vitamin C": ["plasma vitamin c", "vitamin c"],
    "Serum Alpha-Tocopherol": ["serum alpha-tocopherol", "vitamin e"],
    "Thiamine Pyrophosphate (TPP)": ["thiamine pyrophosphate", "vitamin b1"],
    "EGRAC": ["egrac", "riboflavin function", "vitamin b2"],
    "Serum Niacin": ["serum niacin", "vitamin b3"],
    "Serum Pantothenic Acid": ["serum pantothenic acid", "vitamin b5"],
    "Pyridoxal 5-Phosphate (PLP)": ["pyridoxal 5-phosphate", "active vitamin b6"],
    "Serum Biotin": ["serum biotin", "vitamin b7"],
    "Homocysteine (Hcy)": ["homocysteine", "hcy, serum"],
    "Undercarboxylated Osteocalcin": ["undercarboxylated osteocalcin", "vitamin k status"],

    # --- THYROID & HORMONES ---
    "Thyroid Stimulating Hormone (TSH)": ["tsh", "thyroid stimulating hormone", "tsh (ultrasensitive)", "thyrotropin", "tsh-thyroid stimulating hormone"], 
    "Total T3": [ "triiodothyronine", "total t3", "T3-total","T3"], 
    "Total T4": [ "thyroxine", "total t4", "T4-total","T4"], 
    "PSA Total": ["prostate specific antigen", "psa total"],
    # --- MISC ---
    "Omega-3 Index": ["omega-3 index"],
}

def clean_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text