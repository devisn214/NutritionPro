from pdf_working.pdftext import extract_pdf_text
from pdf_working.pdf_table import extract_tables
from pdf_working.pdf_parser import PDFBiomarkerExtractor


def process_pdf(file):
    extractor = PDFBiomarkerExtractor()

    # -------------------------
    # FIRST USE NORMAL TEXT
    # -------------------------
    try:
        print("Using TEXT extraction first")

        text = extract_pdf_text(file)

        results = extractor.extract(text)

        if results:
            return results

    except Exception as e:
        print("Text extraction failed:", e)

    # -------------------------
    # FALLBACK TO TABLE
    # -------------------------
    try:
        print("Using TABLE fallback")

        table_text = extract_tables(file)

        if table_text and table_text.strip():
            results = extractor.extract(table_text)

            if results:
                return results

    except Exception as e:
        print("Table extraction failed:", e)

    return []