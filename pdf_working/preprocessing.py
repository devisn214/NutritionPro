import re

# ---------------- SYNONYMS ----------------
BIOMARKER_SYNONYMS = {
    # --- IRON & ANEMIA ---
    "Serum Ferritin": ["serum ferritin", "ferritin"],
    "Serum Iron": ["serum iron", "iron", "iron, serum"],
    "Transferrin Saturation (TSAT)": ["transferrin saturation", "tsat", "iron saturation"],
    "Hemoglobin": ["hemoglobin"],
    "Hematocrit": ["hematocrit"],

    # --- BLOOD SUGAR & METABOLIC ---
    "HbA1c": ["hba1c","glycosylated hemoglobin","glycosylated haemoglobin","hb a1c"],
    "Fasting Glucose": ["fasting glucose",  "fasting blood sugar", "glucose fasting", "glucose, fluoride plasma","FBS-FASTING BLOOD SUGAR(GLUCOSE)"],
    "Estimated Average Glucose (eAG)": ["estimated average glucose"],
    "Uric Acid": ["Uric acid", "uric acid, serum"],

    # --- LIPIDS (CHOLESTEROL) ---
    "Total Cholesterol": ["cholesterol, total", "total cholesterol","CHOLESTROL-TOTAL"],
    "LDL Cholesterol": ["ldl cholesterol","cholesterol - ldl","cholesterol ldl","bad cholesterol","ldl"],
    "HDL Cholesterol": [ "hdl cholesterol","cholesterol hdl", "cholesterol - hdl","good cholesterol","hdl"],
    "Triglycerides": ["triglycerides"],
    "Non-HDL Cholesterol": ["non hdl cholesterol","NON HDL CHOLESTEROL"],
    "VLDL": ["vldl", "very low density lipoprotein","VLDL CHOLESTROL"],
    "Chol/HDL Ratio": ["chol/hdl ratio", "cholesterol/hdl ratio"],

    # --- KIDNEY FUNCTION ---
    "Creatinine": ["Creatinine", "creatinine, serum", "sr. creatinine"],
    "Urea": ["Urea", "blood urea", "total urea","UREA"],
    "Blood Urea Nitrogen (BUN)": ["Blood Urea Nitrogen", "bun"],

    # --- LIVER & ENZYMES ---
    "Alkaline Phosphatase (ALP)": ["alkaline phosphatase", "alk phos", "alkaline phosphaqtase","ALK PHOS"],
    "Serum Bilirubin": ["serum bilirubin", "bilirubin, total", "total bilirubin", "t. bili","BILIRUBIN-TOTAL"],
    "Bilirubin Direct": ["bilirubin, direct", "direct bilirubin", "d. bili","BILIRUBIN-DIRECT"],
    "Bilirubin Indirect": ["bilirubin, indirect", "indirect bilirubin", "i. bili","BILIRUBIN-INDIRECT"],

    # --- PROTEINS & INFLAMMATION ---
    "Serum Albumin": ["serum albumin", "albumin","Albumin","ALBUMIN"],
    "Total Protein": ["total protein", "protein, total","TOTAL PROTEIN"],
    "Globulin": ["globulin", "globulin, serum","GLOBULIN"],
    "A/G Ratio": ["albumin/globulin ratio", "a/g ratio"],
    "hs-CRP": ["hs-crp", "c-reactive protein", "high sensitivity crp"],
    "ESR": ["erythrocyte sedimentation rate", "sedimentation rate(ESR)"],

    # --- ELECTROLYTES & MINERALS ---
    "Serum Calcium": ["serum calcium", "calcium",  "total calcium"],
    "Ionized Calcium": ["ionized calcium"],
    "Serum Magnesium": ["serum magnesium", "magnesium"],
    "RBC Magnesium": ["rbc magnesium", "magnesium, rbc", "intracellular magnesium"],
    "Serum Sodium": ["serum sodium", "sodium"],
    "Serum Potassium": ["serum potassium", "potassium"],
    "Serum Phosphate": ["serum phosphate", "phosphorus"],

    # --- VITAMINS ---
    "25-Hydroxy Vitamin D": ["25- HYDROXYVITAMIN D", "vitamin d total", "25-oh vit d", "25 - HYDROXYVITAMIN D(VITAMIN D TOTAL),SERUM","25 hydroxy Vitamin D Total", "25-hydroxy vitamin d", "25-hydroxyvitamin d", "25-hydroxy vitamin d, serum"],
    "1-25-Dihydroxy Vitamin D": ["1-25-dihydroxy vitamin d", "calcitriol", "active vitamin d"],
    "Serum Vitamin B12": ["serum vitamin b12", "cobalamin"],
    "Serum Folate": ["serum folate", "folate", "vitamin b9"],
    "Homocysteine (Hcy)": ["homocysteine", "hcy, serum"],

    # --- THYROID & HORMONES ---
    "TSH": ["tsh", "thyroid stimulating hormone", "tsh (ultrasensitive)", "thyrotropin","TSH-THYROID STIMULATING HORMONE"],
    "T3": ["t3", "triiodothyronine", "total t3","T3-Total"],
    "T4": ["t4", "thyroxine", "total t4","T4-Total"],
    "PSA Total": ["prostate specific antigen", "psa total"]
}

def clean_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text