import zlib
import fitz  # PyMuPDF
import PyPDF2
import os
from statistics import mean
from PyPDF2.errors import PdfReadError

def extract_suspicious_elements(pdf_path):
    """
    Extract suspicious elements like OpenAction, JavaScript, and EmbeddedFiles from a PDF.
    """
    suspicious_elements = []

    print(f"Processing file: {pdf_path}")

    try:
        # Using PyMuPDF to extract elements
        doc = fitz.open(pdf_path)
        for i in range(len(doc)):  # Iterate through the pages
            page = doc.load_page(i)
            # Check for JavaScript actions in annotations
            annots = page.annots()
            if annots:
                for annot in annots:
                    if annot.type[0] == 12:  # JavaScript action
                        suspicious_elements.append(str(annot.info))

            # Check OpenAction, which can trigger JavaScript
            if "/OpenAction" in page.get_text("raw"):
                suspicious_elements.append(f"OpenAction found on page {page.number}")
    except Exception as e:
        print(f"Error extracting elements with PyMuPDF from {pdf_path}: {e}")

    # Use PyPDF2 to extract JavaScript and EmbeddedFiles
    try:
        with open(pdf_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            # Check for JavaScript at the document level
            if reader.trailer.get("/Root") and reader.trailer["/Root"].get("/Names"):
                names = reader.trailer["/Root"]["/Names"]
                if names.get("/JavaScript"):
                    js_dict = names["/JavaScript"]
                    if js_dict.get("/Names"):
                        js_entries = js_dict["/Names"]
                        for i in range(1, len(js_entries), 2):
                            suspicious_elements.append(str(js_entries[i].get_object()))
            # Check for JavaScript in page annotations
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                if "/Annots" in page:
                    annots = page.get("/Annots")
                    if isinstance(annots, list):
                        for annot_ref in annots:
                            annot = annot_ref.get_object()
                            if annot.get("/Subtype") == "/Widget" and annot.get("/AA"):
                                aa = annot["/AA"]
                                if aa.get("/JS"):
                                    suspicious_elements.append(str(aa["/JS"]))
            # Check for additional JavaScript actions (e.g., /AA, /OpenAction)
            if reader.trailer.get("/Root") and reader.trailer["/Root"].get("/OpenAction"):
                open_action = reader.trailer["/Root"]["/OpenAction"]
                if open_action.get("/JS"):
                    suspicious_elements.append(f"OpenAction JavaScript: {str(open_action.get('/JS'))}")
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                for key in ["/AA", "/OpenAction", "/AcroForm"]:
                    if key in page:
                        action = page.get(key)
                        if action and isinstance(action, PyPDF2.generic.DictionaryObject):
                            if action.get("/S") == "/JavaScript" and action.get("/JS"):
                                suspicious_elements.append(f"JavaScript found in {key} on page {page_num}: {action.get('/JS')}")
    except (PdfReadError, Exception) as e:
        print(f"Error extracting JavaScript with PyPDF2 from {pdf_path}: {e}")

    return "\n".join(suspicious_elements)

def calculate_kolmogorov_complexity(data):
    """
    Calculate an approximation of Kolmogorov Complexity by compressing the data and
    returning the length of the compressed data.
    """
    compressed_data = zlib.compress(data.encode('utf-8'))
    return len(compressed_data)

def kolmogorov_complexity_of_pdf(pdf_path):
    """
    Calculate the Kolmogorov Complexity of a PDF by extracting its suspicious elements
    and calculating the complexity of that data.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file '{pdf_path}' not found.")

    # Extract suspicious elements from the PDF
    suspicious_data = extract_suspicious_elements(pdf_path)

    # If suspicious data is empty, use the raw PDF content for complexity calculation
    if not suspicious_data:
        print(f"No suspicious elements found in PDF file '{pdf_path}'. Using raw content for complexity calculation.")
        with open(pdf_path, "rb") as pdf_file:
            suspicious_data = pdf_file.read()

    # Calculate Kolmogorov Complexity
    if isinstance(suspicious_data, bytes):
        complexity = calculate_kolmogorov_complexity(suspicious_data.decode('latin1'))
    else:
        complexity = calculate_kolmogorov_complexity(suspicious_data)
    return complexity

def process_directory(directory, label):
    """
    Process all PDF files in a directory and return their Kolmogorov complexities.
    """
    complexities = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                print(f"Processing file: {pdf_path}")
                try:
                    complexity = kolmogorov_complexity_of_pdf(pdf_path)
                    complexities.append(complexity)
                    print(f"Kolmogorov Complexity for {pdf_path}: {complexity}")
                except Exception as e:
                    print(f"Error processing file {pdf_path}: {e}")
    
    with open(f"{label}_complexities.txt", "w") as f:
        for complexity in complexities:
            f.write(f"{complexity}\n")
    
    return complexities

def main(clean_dir, dirty_dir):
    """
    Main function to process two directories (clean and dirty), calculate Kolmogorov complexities,
    save the output to files, and print the means.
    """
    print(f"Processing clean directory: {clean_dir}")
    clean_complexities = process_directory(clean_dir, "clean")
    print(f"Processing dirty directory: {dirty_dir}")
    dirty_complexities = process_directory(dirty_dir, "dirty")

    clean_mean = mean(clean_complexities) if clean_complexities else 0
    dirty_mean = mean(dirty_complexities) if dirty_complexities else 0

    print(f"Mean Kolmogorov Complexity for clean PDFs: {clean_mean}")
    print(f"Mean Kolmogorov Complexity for dirty PDFs: {dirty_mean}")

if __name__ == "__main__":
    clean_directory = "clean"  # Replace with your clean PDF directory path
    dirty_directory = "dirty"  # Replace with your dirty PDF directory path
    main(clean_directory, dirty_directory)
