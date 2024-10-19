import os
import argparse
import requests
import logging
import threading
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

def download_pdf(url, output_folder, source_name):
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
                return True  # New file downloaded
            else:
                logging.warning(f"[{source_name}] URL does not point to a PDF: {url}")
                return False
        else:
            logging.error(f"[{source_name}] Failed to download {url}: HTTP Status Code {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"[{source_name}] Exception occurred while downloading {url}: {e}")
        return False

def download_from_source(name, source_function, num_pdfs, output_folder):
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
            if download_pdf(url, output_folder, name):
                count += 1
        start += batch_size
    logging.info(f"Downloaded {count} new PDFs from {name}")

def download_pdfs(output_folder, num_pdfs):
    sources = [
        {
            'name': 'arXiv',
            'function': get_arxiv_pdf_links,
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
            args=(source['name'], source['function'], num_to_download, output_folder)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logging.info("Download completed.")

def get_arxiv_pdf_links(num_pdfs, start=0):
    pdf_links = []
    try:
        base_url = 'http://export.arxiv.org/api/query'
        params = {
            'search_query': 'all',
            'start': start,
            'max_results': num_pdfs,
            'sortBy': 'lastUpdatedDate',
            'sortOrder': 'descending'
        }
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            for entry in entries:
                arxiv_id = entry.find('atom:id', ns).text.split('/abs/')[-1]
                pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
                pdf_links.append(pdf_url)
        else:
            logging.error(f"Error fetching arXiv links: HTTP Status {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching arXiv links: {e}")
    return pdf_links

def main(output_folder, num_pdfs):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    os.makedirs(output_folder, exist_ok=True)
    download_pdfs(output_folder, num_pdfs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download Diverse Clean PDFs')
    parser.add_argument('--output_folder', default='clean_pdfs', help='Output folder to save PDFs')
    parser.add_argument('--num_pdfs', type=int, default=40, help='Total number of PDFs to download')
    args = parser.parse_args()

    main(args.output_folder, args.num_pdfs)
