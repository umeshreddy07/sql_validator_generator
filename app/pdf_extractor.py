import fitz  # PyMuPDF
import re

def extract_sql_from_pdf(pdf_file):
    """
    Extracts text from a PDF and uses regex to find potential SQL queries.
    Assumes queries are separated by question numbers like '1.', '2.', etc.
    """
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        # This regex looks for text between a number and a semicolon, which is a common pattern for SQL answers.
        # It's a simple approach and might need refinement based on the students' answer format.
        queries = re.findall(r'\d+\.\s*(SELECT.*?);', full_text, re.DOTALL | re.IGNORECASE)
        
        # Clean up the extracted queries
        cleaned_queries = [q.strip().replace('\n', ' ') for q in queries]
        
        return cleaned_queries, None
    except Exception as e:
        return None, f"Failed to process PDF: {e}" 