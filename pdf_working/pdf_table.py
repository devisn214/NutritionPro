import camelot
import pandas as pd

def extract_tables(file_path):
    try:
        tables = camelot.read_pdf(file_path, pages="all", flavor="stream")

        all_rows = []

        for table in tables:
            df = table.df

            for _, row in df.iterrows():
                row_text = " ".join([str(x) for x in row if x])
                all_rows.append(row_text)

        return "\n".join(all_rows)

    except Exception:
        return ""