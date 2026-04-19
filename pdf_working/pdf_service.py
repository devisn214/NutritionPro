from pdf_working.pdftext import extract_pdf_text
from pdf_working.pdf_table import extract_tables
from pdf_working.pdf_parser import PDFBiomarkerExtractor


def process_pdf(file):
    extractor = PDFBiomarkerExtractor()

    try:
        table_text = extract_tables(file)

        if table_text and table_text.strip():
            results = extractor.extract(table_text)

            if results:
                print("Using TABLE extraction")
                return results

    except Exception as e:
        print("Table extraction failed:", e)

    print("Using TEXT extraction")

    text = extract_pdf_text(file)

    return extractor.extract(text)