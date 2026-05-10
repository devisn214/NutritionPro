# unit_converter.py

def normalize_unit(u):
    if not u:
        return ""

    u = u.lower().strip()

    # ===== SYMBOL FIXES =====
    u = u.replace("µ", "u")
    u = u.replace("μ", "u")
    u = u.replace("myu", "u")   # your special case

    # ===== STANDARDIZATION =====
    replacements = {
        "ug": "mcg",
        "u g": "mcg",
        "iu/ml": "iu/ml",
        "u/l": "u/l",
        "iu/l": "iu/l",
        "miu/l": "miu/l",
        "miu/ml": "miu/ml",
    }

    for k, v in replacements.items():
        u = u.replace(k, v)

    return u


# ============================================================
# CONVERSION TABLE (TO STANDARD UNITS)
# ============================================================

UNIT_CONVERSION = {

    # ===== MASS CONVERSIONS =====
    "mg/dl": {
        "mg/dl": 1,
        "g/dl": 1000,        # 1 g/dL = 1000 mg/dL
        "mmol/l": 18.0,      # glucose (approx)
    },

    "mcg/dl": {
        "mcg/dl": 1,
        "mg/dl": 1000,
    },

    "ng/ml": {
        "ng/ml": 1,
        "ng/dl": 0.01,       # 1 ng/dL = 0.01 ng/mL
        "pg/ml": 0.001,      # 1 pg/mL = 0.001 ng/mL
    },

    "pg/ml": {
        "pg/ml": 1,
        "ng/ml": 1000,
    },

    # ===== ELECTROLYTES =====
    "mmol/l": {
        "mmol/l": 1,
        "meq/l": 1,
    },

    # ===== CALCIUM / MAGNESIUM =====
    "mg/dl": {
        "mg/dl": 1,
        "mmol/l": 4.0,   # calcium approx
    },

    # ===== CHOLESTEROL =====
    "mg/dl": {
        "mg/dl": 1,
        "mmol/l": 38.67,
    },

    # ===== VITAMIN D =====
    "ng/ml": {
        "ng/ml": 1,
        "nmol/l": 0.4,
    },

    # ===== ENZYMES =====
    "u/l": {
        "u/l": 1,
        "iu/l": 1,
    },

    # ===== HORMONES (TSH etc) =====
    "miu/l": {
        "miu/l": 1,
        "uiu/ml": 1,      # µIU/mL ≈ mIU/L
        "iu/ml": 1,
    },

    # ===== PERCENT =====
    "%": {
        "%": 1
    }
}


# ============================================================
# MAIN CONVERTER
# ============================================================

def convert_value(value, from_unit, to_unit):

    if value is None:
        return None

    from_unit = normalize_unit(from_unit)
    to_unit = normalize_unit(to_unit)

    if not from_unit:
        return value

    if from_unit == to_unit:
        return value

    if to_unit in UNIT_CONVERSION:
        mapping = UNIT_CONVERSION[to_unit]

        if from_unit in mapping:
            return value * mapping[from_unit]

    # fallback → no conversion
    return value