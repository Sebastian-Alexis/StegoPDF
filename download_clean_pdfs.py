import os
import argparse
import requests
import logging
import threading
from urllib.parse import urljoin, urlparse
import fitz  # PyMuPDF
import PyPDF2
from PyPDF2.generic import IndirectObject
import signal
import sys
import time

def download_pdf(url, output_folder, source_name, benign_js_only):
    try:
        filename = os.path.basename(urlparse(url).path)
        file_path = os.path.join(output_folder, filename)
        if os.path.exists(file_path):
            logging.info(f"[{source_name}] File already exists: {filename}")
            return False  # File already exists; do not count towards new downloads

        headers = {'User-Agent': 'Mozilla/5.0 (compatible; PDFDownloader/1.0)'}
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logging.info(f"[{source_name}] Downloaded: {filename}")
                time.sleep(0.1)  # Allow for interruption
                if has_javascript(file_path):
                    if benign_js_only:
                        if is_benign_javascript(file_path):
                            return True  # New file downloaded
                        else:
                            os.remove(file_path)  # Remove PDF if JavaScript is not benign
                            logging.info(f"[{source_name}] Removed: {filename} (Non-benign JavaScript found)")
                            return False
                    return True
                else:
                    os.remove(file_path)  # Remove PDF if it doesn't contain JavaScript
                    logging.info(f"[{source_name}] Removed: {filename} (No JavaScript found)")
                    return False
            else:
                logging.warning(f"[{source_name}] URL does not point to a PDF: {url}")
                return False
        else:
            logging.error(f"[{source_name}] Failed to download {url}: HTTP Status Code {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"[{source_name}] Exception occurred while downloading {url}: {e}")
        return False

def has_javascript(pdf_path):
    try:
        # Check for JavaScript with PyMuPDF
        document = fitz.open(pdf_path)
        for page_number in range(len(document)):
            page = document.load_page(page_number)
            annot = page.first_annot
            while annot:
                if annot.type[0] == 21:  # Check if annotation is JavaScript
                    document.close()
                    return True
                annot = annot.next
        document.close()

        # Check for JavaScript with PyPDF2
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            if "/Names" in reader.trailer.get("/Root", {}):
                names = reader.trailer["/Root"]["/Names"]
                if isinstance(names, IndirectObject):
                    names = names.get_object()
                if "/JavaScript" in names:
                    return True
        return False
    except Exception as e:
        logging.error(f"Error checking JavaScript in PDF {pdf_path}: {e}")
        return False

def is_benign_javascript(pdf_path):
    try:
        # Add logic here to determine if the JavaScript is benign
        # For now, we assume all JavaScript is benign
        return True
    except Exception as e:
        logging.error(f"Error checking if JavaScript is benign in PDF {pdf_path}: {e}")
        return False

def download_from_source(name, source_function, num_pdfs, output_folder, benign_js_only):
    count = 0
    start = 0
    batch_size = 100  # Number of PDFs to fetch in each batch
    while count < num_pdfs:
        urls = source_function(batch_size, start)
        if not urls:
            break  # No more URLs to process
        for url in urls:
            if count >= num_pdfs:
                break
            if download_pdf(url, output_folder, name, benign_js_only):
                count += 1
            time.sleep(0.1)  # Allow for interruption
        start += batch_size
    logging.info(f"Downloaded {count} new PDFs from {name}")

def download_pdfs(output_folder, num_pdfs, benign_js_only):
    sources = [
        {
            'name': 'ProjectGutenberg',
            'function': get_project_gutenberg_pdf_links,
        },
    ]

    threads = []
    num_sources = len(sources)
    pdfs_per_source = num_pdfs // num_sources
    remaining_pdfs = num_pdfs % num_sources

    for i, source in enumerate(sources):
        num_to_download = pdfs_per_source + (1 if i < remaining_pdfs else 0)
        thread = threading.Thread(
            target=download_from_source,
            args=(source['name'], source['function'], num_to_download, output_folder, benign_js_only)
        )
        threads.append(thread)
        thread.start()

    try:
        for thread in threads:
            while thread.is_alive():
                thread.join(timeout=0.1)  # Allow for interruption
    except KeyboardInterrupt:
        logging.warning("Download interrupted by user.")
        for thread in threads:
            if thread.is_alive():
                logging.warning(f"Stopping thread: {thread.name}")
        sys.exit(1)

    logging.info("Download completed.")

def get_project_gutenberg_pdf_links(num_pdfs, start=0):
    pdf_links = []
    try:
        # Using Project Gutenberg as a source of public domain PDFs
        base_url = 'https://www.gutenberg.org/ebooks/search/?query=&submit_search=Go&start_index=' + str(start)
        response = requests.get(base_url)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            books = soup.find_all('li', class_='booklink')
            for book in books:
                if len(pdf_links) >= num_pdfs:
                    break
                book_link = book.find('a', href=True)
                if book_link:
                    book_page_url = urljoin(base_url, book_link['href'])
                    book_page_response = requests.get(book_page_url, allow_redirects=True)
                    if book_page_response.status_code == 200:
                        book_soup = BeautifulSoup(book_page_response.content, 'html.parser')
                        # Broaden search for PDF links
                        pdf_link = book_soup.find('a', href=True, string=lambda s: s and 'pdf' in s.lower())
                        if pdf_link:
                            full_pdf_link = urljoin(book_page_url, pdf_link['href'])
                            logging.debug(f"Found PDF link: {full_pdf_link}")
                            pdf_links.append(full_pdf_link)
                        else:
                            logging.debug(f"No PDF link found on page: {book_page_url}")
                    else:
                        logging.error(f"Error fetching book page: HTTP Status {book_page_response.status_code} for URL {book_page_url}")
        else:
            logging.error(f"Error fetching Project Gutenberg links: HTTP Status {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching Project Gutenberg links: {e}")
    return pdf_links

def main(output_folder, num_pdfs, benign_js_only):
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    os.makedirs(output_folder, exist_ok=True)
    try:
        download_pdfs(output_folder, num_pdfs, benign_js_only)
    except KeyboardInterrupt:
        logging.warning("Download process interrupted by user.")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download Diverse Clean PDFs')
    parser.add_argument('--output_folder', default='clean_pdfs', help='Output folder to save PDFs')
    parser.add_argument('--num_pdfs', type=int, default=50, help='Total number of PDFs to download')
    parser.add_argument('--benign_js_only', action='store_true', help='Only download PDFs with benign JavaScript')
    args = parser.parse_args()

    main(args.output_folder, args.num_pdfs, args.benign_js_only)
