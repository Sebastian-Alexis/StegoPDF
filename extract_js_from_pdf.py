import fitz  # PyMuPDF
import PyPDF2
import sys

def extract_javascript_with_pymupdf(pdf_path):
    try:
        # Open the PDF with PyMuPDF
        document = fitz.open(pdf_path)
        
        # Extract JavaScript from embedded annotations or objects
        javascript_list = []
        for page_number in range(len(document)):
            page = document.load_page(page_number)
            annot = page.first_annot
            while annot:
                if annot.type[0] == 21:  # Check if annotation is JavaScript
                    javascript_list.append(annot.info.get("content"))
                annot = annot.next

        # Close the document
        document.close()

        # Output the JavaScript code
        if javascript_list:
            print("JavaScript found in PDF with PyMuPDF:\n")
            for index, js_code in enumerate(javascript_list):
                print(f"JavaScript #{index + 1}:\n{js_code}\n")
        else:
            print("No JavaScript found with PyMuPDF.")
    except Exception as e:
        print(f"An error occurred with PyMuPDF: {e}")

def extract_javascript_with_pypdf2(pdf_path):
    try:
        # Open the PDF with PyPDF2
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            javascript_list = []

            # Extract JavaScript from the catalog (document-level JavaScript)
            if "/Names" in reader.trailer["/Root"]:
                names = reader.trailer["/Root"]["/Names"]
                if "/JavaScript" in names:
                    js_dict = names["/JavaScript"]["/Names"]
                    for i in range(1, len(js_dict), 2):
                        javascript = js_dict[i].get_object()
                        javascript_list.append(javascript.get("/JS"))

            # Output the JavaScript code
            if javascript_list:
                print("JavaScript found in PDF with PyPDF2:\n")
                for index, js_code in enumerate(javascript_list):
                    print(f"JavaScript #{index + 1}:\n{js_code}\n")
            else:
                print("No JavaScript found with PyPDF2.")
    except Exception as e:
        print(f"An error occurred with PyPDF2: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_js_from_pdf.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    extract_javascript_with_pymupdf(pdf_path)
    extract_javascript_with_pypdf2(pdf_path)

if __name__ == "__main__":
    main()
