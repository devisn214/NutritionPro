import pandas as pd


class GenomeParser:

    def __init__(self, gene_csv_path):

        self.gene_df = pd.read_csv(gene_csv_path)

        self.gene_df["rsid"] = self.gene_df["rsid"].astype(str).str.strip()

        self.gene_df["genotype"] = self.gene_df["genotype"].astype(str).str.upper().str.strip()

    def load_genome_file(self, genome_file_path):

        try:

            header_index = None

            with open(genome_file_path, "r", encoding="utf-8", errors="ignore") as f:

                lines = f.readlines()

            for i, line in enumerate(lines):

                clean = line.strip().lower()

                if "rsid" in clean and "genotype" in clean:

                    header_index = i

                    break

            if header_index is not None:

                df = pd.read_csv(genome_file_path, sep="\t", skiprows=header_index, dtype=str)

            else:

                df = pd.read_csv(genome_file_path, sep="\t", dtype=str)

        except Exception:

            df = pd.read_csv(genome_file_path, dtype=str)

        df.columns = [str(c).replace("#", "").strip().lower() for c in df.columns]

        return df

    def find_rsid_column(self, df):

        possible = ["rsid", "rs_id", "snp", "marker"]

        for col in df.columns:

            if col.lower() in possible:

                return col

        return None

    def find_genotype_column(self, df):

        possible = ["genotype", "result", "alleles", "call"]

        for col in df.columns:

            if col.lower() in possible:

                return col

        if "allele1" in df.columns and "allele2" in df.columns:

            df["genotype"] = df["allele1"].fillna("") + df["allele2"].fillna("")

            return "genotype"

        return None

    def extract_variants(self, genome_file_path):

        df = self.load_genome_file(genome_file_path)

        rsid_col = self.find_rsid_column(df)

        genotype_col = self.find_genotype_column(df)

        if not rsid_col or not genotype_col:

            print("Could not detect rsid/genotype")

            return []

        df["rsid"] = df[rsid_col].astype(str).str.strip()

        df["genotype"] = df[genotype_col].astype(str).str.upper().str.strip()

        df = df[df["rsid"].str.startswith("rs")]

        merged = pd.merge(df, self.gene_df, on=["rsid", "genotype"], how="inner")
        print(f"Found {len(merged)} matching variants in genome file.")

        results = []

        for _, row in merged.iterrows():

            results.append({

                "gene": row["gene_symbol"],

                "gene_fullname": row["gene_fullname"],

                "rsid": row["rsid"],

                "genotype": row["genotype"],

                "nutrient_id": row["affected_nutrient"],

                "description": row["description"],

                "impact": row["impact"],

                "action": row["action"],

                "direction": row["direction"],

                "variant_effect": row["variant_effect"]

            })

        return results