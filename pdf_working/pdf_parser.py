import re
from pdf_working.preprocessing import BIOMARKER_SYNONYMS


class PDFBiomarkerExtractor:

    def __init__(self):
        pass

    # -------------------------------------------------
    # STRONG NORMALIZATION
    # -------------------------------------------------
    def normalize(self, text):
        text = text.lower().strip()

        # Replace punctuation with spaces
        text = re.sub(r"[\(\)\[\],:/_\-]", " ", text)

        # Remove unwanted symbols
        text = re.sub(r"[^a-z0-9.%+ ]", "", text)

        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # -------------------------------------------------
    # SMART NAME MATCHING
    # -------------------------------------------------
    def match_name(self, line):
        clean = self.normalize(line)

        for std_name, aliases in BIOMARKER_SYNONYMS.items():

            # LONGER aliases first
            sorted_aliases = sorted(aliases, key=len, reverse=True)

            for alias in sorted_aliases:
                alias_clean = self.normalize(alias)

                # containment match
                if alias_clean in clean:
                    return std_name, alias_clean

        return None, None

    # -------------------------------------------------
    # UNIT EXTRACTION
    # -------------------------------------------------
    def get_unit(self, line):
        m = re.search(
            r"(mg/dl|g/dl|ng/ml|pg/ml|u/l|iu/ml|mm/hr|%|ratio|µg/dl|µiu/ml|mcg/dl)",
            line.lower()
        )

        if m:
            return m.group(1)

        return ""

    # -------------------------------------------------
    # VALUE SAME LINE
    # -------------------------------------------------
    def extract_value_same_line(self, line, alias):
        clean = self.normalize(line)

        pos = clean.find(alias)

        if pos == -1:
            return None

        remain = clean[pos + len(alias):].strip()

        if not remain:
            return None

        # Remove ranges like 70-100
        remain = re.sub(r"\d+\s*-\s*\d+", "", remain)

        nums = re.findall(r"\d+\.\d+|\d+", remain)

        if nums:
            try:
                return float(nums[0])
            except:
                return None

        return None

    # -------------------------------------------------
    # VALUE NEXT LINES
    # -------------------------------------------------
    def extract_value_next_lines(self, lines, i):

        blocked = [
            "reference", "range", "adult", "male", "female",
            "method", "units", "normal", "prediabetes",
            "diabetes", "risk", "desirable", "interpretation",
            "page", "view report", "drawn", "received",
            "reported", "accession", "patient"
        ]

        for j in range(1, 6):

            if i + j >= len(lines):
                break

            nxt = lines[i + j].strip()

            if not nxt:
                continue

            low = nxt.lower()

            if any(word in low for word in blocked):
                continue

            # Skip ranges
            if re.search(r"\d+\s*-\s*\d+", nxt):
                continue

            # Skip < or >
            if "<" in nxt or ">" in nxt:
                continue

            nums = re.findall(r"\d+\.\d+|\d+", nxt)

            if len(nums) == 1:
                try:
                    val = float(nums[0])

                    # ESR false catch avoid
                    if "hr" in low and val < 5:
                        continue

                    return val
                except:
                    pass

            if len(nums) >= 1 and ("high" in low or "low" in low):
                try:
                    return float(nums[0])
                except:
                    pass

        return None

    # -------------------------------------------------
    # MAIN EXTRACTION
    # -------------------------------------------------
    def extract(self, text):

        lines = text.splitlines()

        results = []
        used = set()

        for i, line in enumerate(lines):

            line = line.strip()

            if not line:
                continue

            biomarker, alias = self.match_name(line)

            if not biomarker:
                continue

            if biomarker in used:
                continue

            value = self.extract_value_same_line(line, alias)
            unit = self.get_unit(line)

            # If not same line, check next lines
            if value is None:

                value = self.extract_value_next_lines(lines, i)

                for j in range(1, 4):
                    if i + j < len(lines):
                        unit = self.get_unit(lines[i + j]) or unit

            if value is not None:

                results.append({
                    "name": biomarker,
                    "value": value,
                    "unit": unit
                })

                used.add(biomarker)

        return results

    def parse(self, text):
        return self.extract(text)