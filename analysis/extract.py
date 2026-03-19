import fitz  # PyMuPDF
import pdfminer.high_level
import pdfminer.layout
import PyPDF2
import os
from io import BytesIO


def extract_suspicious_elements(pdf_path):
    suspicious_elements = {
        "OpenAction": [],
        "JavaScript": [],
        "EmbeddedFiles": []
    }

    # Using PyMuPDF to extract elements
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):  # Iterate through the pages
        page = doc.load_page(i)
        # Check for JavaScript actions in annotations
        annots = page.annots()
        if annots:
            for annot in annots:
                if annot.type[0] == 12:  # JavaScript action
                    suspicious_elements["JavaScript"].append(annot.info)

        # Check OpenAction, which can trigger JavaScript
        if "/OpenAction" in page.get_text("raw"):  # Look for OpenAction in the raw text
            suspicious_elements["OpenAction"].append(page.number)

    # Use pdfminer to extract JavaScript and EmbeddedFiles
    with open(pdf_path, 'rb') as pdf_file:
        pdf_content = pdf_file.read()
        fp = BytesIO(pdf_content)
        try:
            # Extract text from PDF to check for JavaScript and EmbeddedFiles
            text = pdfminer.high_level.extract_text(fp)
            if '/JavaScript' in text:
                suspicious_elements["JavaScript"].append("JavaScript found in content stream")
            if '/EmbeddedFile' in text:
                suspicious_elements["EmbeddedFiles"].append("Embedded file found in content stream")
        except Exception as e:
            print(f"Error extracting text with pdfminer: {e}")

    # Use PyPDF2 to extract JavaScript
    try:
        with open(pdf_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            # Check for JavaScript at the document level
            if reader.trailer["/Root"].get("/Names"):
                names = reader.trailer["/Root"]["/Names"]
                if names.get("/JavaScript"):
                    js_dict = names["/JavaScript"]
                    if js_dict.get("/Names"):
                        js_entries = js_dict["/Names"]
                        for i in range(1, len(js_entries), 2):
                            suspicious_elements["JavaScript"].append(js_entries[i].get_object())
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
                                    suspicious_elements["JavaScript"].append(aa["/JS"])
    except Exception as e:
        print(f"Error extracting JavaScript with PyPDF2: {e}")

    return suspicious_elements


if __name__ == "__main__":
    pdf_path = "dirty\dirty_2106.14725v2.pdf_script_behavior.pdf"  # Replace with your PDF file path
    elements = extract_suspicious_elements(pdf_path)
    print("Suspicious Elements Found:")
    for key, value in elements.items():
        print(f"{key}: {value}")
