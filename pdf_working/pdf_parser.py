import re
from pdf_working.preprocessing import BIOMARKER_SYNONYMS


class PDFBiomarkerExtractor:

    def __init__(self):
        pass

    def normalize(self, text):
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def match_name(self, line):
        clean = self.normalize(line)

        for std_name, aliases in BIOMARKER_SYNONYMS.items():
            for alias in aliases:
                alias_clean = self.normalize(alias)

                if clean.startswith(alias_clean):
                    return std_name, alias_clean

        return None, None

    def get_unit(self, line):
        m = re.search(
            r"(mg/dl|g/dl|ng/ml|pg/ml|u/l|iu/ml|mm/hr|%|ratio|µg/dl|µiu/ml)",
            line.lower()
        )

        if m:
            return m.group(1)

        return ""

    def extract_value_same_line(self, line, alias):
        clean = self.normalize(line)
        remain = clean[len(alias):].strip()

        if not remain:
            return None

        if re.search(r"\d+\s*-\s*\d+", remain):
            remain = re.sub(r"\d+\s*-\s*\d+", "", remain)

        nums = re.findall(r"\d+\.\d+|\d+", remain)

        if nums:
            try:
                return float(nums[0])
            except:
                return None

        return None

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
            low = nxt.lower()

            if not nxt:
                continue

            if any(word in low for word in blocked):
                continue

            if re.search(r"\d+\s*-\s*\d+", nxt):
                continue

            if "<" in nxt or ">" in nxt:
                continue

            nums = re.findall(r"\d+\.\d+|\d+", nxt)

            if len(nums) == 1:
                try:
                    val = float(nums[0])

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