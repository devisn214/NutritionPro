import re
from pdf_working.preprocessing import BIOMARKER_SYNONYMS


class PDFBiomarkerExtractor:
    def __init__(self):
        self.unit_pattern = re.compile(
            r"(mg/dl|g/dl|ng/ml|pg/ml|u/l|iu/ml|miu/ml|µiu/ml|mm/hr|mmol/l|µg/dl|ng/dl|mcg/dl|nmol/l|micromol/l|%)",
            re.IGNORECASE
        )

    def normalize(self, text):
        text = text.lower().strip()
        text = re.sub(r"[\(\)\[\],:/_\-]", " ", text)
        text = re.sub(r"[^a-z0-9.%+ ]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def is_short_alias(self, alias):
        return len(alias) <= 3

    def match_name(self, line):
        clean = self.normalize(line)

        for std_name, aliases in BIOMARKER_SYNONYMS.items():

            aliases = sorted(aliases, key=len, reverse=True)

            for alias in aliases:

                alias_clean = self.normalize(alias)

                pattern = (
                    r"(?<![a-z0-9])"
                    + re.escape(alias_clean)
                    + r"(?![a-z0-9])"
                )

                match = re.search(pattern, clean)

                if not match:
                    continue

                if re.match(r"^\d+", alias_clean):
                    continue

                if self.is_short_alias(alias_clean):

                    skip = False

                    for _, aliases_2 in BIOMARKER_SYNONYMS.items():

                        for long_alias in aliases_2:

                            long_alias_clean = self.normalize(long_alias)

                            if long_alias_clean == alias_clean:
                                continue

                            long_pattern = (
                                r"(?<![a-z0-9])"
                                + re.escape(long_alias_clean)
                                + r"(?![a-z0-9])"
                            )

                            if re.search(long_pattern, clean):
                                skip = True
                                break

                        if skip:
                            break

                    if skip:
                        continue

                if alias_clean in ["t3", "total t3"]:
                    if re.search(r"\bft3\b|free triiodothyronine", clean):
                        continue

                if alias_clean in ["t4", "total t4"]:
                    if re.search(r"\bft4\b|free thyroxine", clean):
                        continue

                return std_name, alias_clean

        return None, None

    def is_header_line(self, line):
        return "," in line and not re.search(r"\d", line)

    def get_unit(self, line):
        m = self.unit_pattern.search(line.lower())
        return m.group(1).lower() if m else ""

    def remove_ranges(self, text):
        text = re.sub(r"\d+(\.\d+)?\s*-\s*\d+(\.\d+)?", " ", text)
        text = re.sub(r"<\s*\d+(\.\d+)?", " ", text)
        text = re.sub(r">\s*\d+(\.\d+)?", " ", text)
        return text

    def clean_after_alias(self, line, alias):
        clean = self.normalize(line)

        match = re.search(
            r"\b" + re.escape(alias) + r"\b",
            clean
        )

        if not match:
            return ""

        remain = clean[match.end():].strip()

        remain = self.remove_ranges(remain)

        return remain

    def is_blocked_line(self, text):
        blocked = [
            "reference", "range", "page", "doctor", "reg no",
            "reported", "drawn", "received", "patient",
            "accession", "years", "method", "view report",
            "interpretation", "units", "adult", "male",
            "female", "normal", "prediabetes", "diabetes",
            "risk", "desirable", "comments", "package",
            "consultant", "technologist", "final results",
            "deficient", "sufficient", "toxicity"
        ]

        low = text.lower()

        return any(word in low for word in blocked)

    def extract_value_same_line(self, line, alias):
        remain = self.clean_after_alias(line, alias)

        if not remain:
            return None

        nums = re.findall(r"\b\d+\.\d+|\b\d+\b", remain)

        nums = [
            n for n in nums
            if 0 <= float(n) <= 5000
        ]

        if not nums:
            return None

        return float(nums[0])

    def extract_value_next_lines(self, lines, i):
        for j in range(1, 3):

            if i + j >= len(lines):
                break

            nxt = lines[i + j].strip()

            if not nxt:
                continue

            if self.is_blocked_line(nxt):
                continue

            nxt_clean = self.normalize(nxt)

            if re.match(r"^\d+\s*-?", nxt_clean):
                continue

            nxt = self.remove_ranges(nxt)

            nums = re.findall(r"\b\d+\.\d+|\b\d+\b", nxt)

            nums = [
                n for n in nums
                if 0 <= float(n) <= 5000
            ]

            if len(nums) == 1:
                return float(nums[0])

        return None

    def extract_unit_nearby(self, lines, i):
        for j in range(0, 4):

            if i + j >= len(lines):
                break

            unit = self.get_unit(lines[i + j])

            if unit:
                return unit

        return ""

    def extract(self, text):
        lines = text.splitlines()

        results = []
        used = set()

        for i, line in enumerate(lines):

            line = line.strip()

            if not line:
                continue

            if self.is_header_line(line):
                continue

            biomarker, alias = self.match_name(line)

            if not biomarker:
                continue

            if biomarker in used:
                continue

            value = self.extract_value_same_line(line, alias)

            if value is None:
                value = self.extract_value_next_lines(lines, i)

            if value is None:
                continue

            unit = self.extract_unit_nearby(lines, i)

            results.append({
                "name": biomarker,
                "value": value,
                "unit": unit
            })

            used.add(biomarker)

        return results

    def parse(self, text):
        return self.extract(text)