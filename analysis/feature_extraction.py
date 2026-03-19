import os
import argparse
import pandas as pd
import fitz  # PyMuPDF
import numpy as np
import logging
import re
import asyncio
import aiofiles
import concurrent.futures

async def extract_pdf_features(file_path):
    features = {}
    try:
        # Check if file exists
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        logging.info(f"Attempting to open file: {file_path}")
        # Initialize reader
        doc = fitz.open(file_path)

        # Feature 1: Number of JavaScript Elements and Total Size
        num_javascript = 0
        javascript_total_size = 0
        if doc.is_pdf:
            for xref in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(xref)
                    if '/JavaScript' in obj or '/JS' in obj:
                        num_javascript += 1
                        # Estimate size of JavaScript code
                        stream = doc.xref_stream(xref)
                        if stream:
                            javascript_total_size += len(stream)
                except Exception as e:
                    logging.debug(f"Error processing object {xref} in {file_path}: {e}")
                    continue
        features['num_javascript'] = num_javascript
        features['javascript_total_size'] = javascript_total_size

        # Feature 2: Presence of Suspicious Actions
        # Actions like /Launch, /OpenAction, /AA can be used to execute code
        has_suspicious_actions = 0
        suspicious_actions = ['/Launch', '/OpenAction', '/AA']
        if doc.is_pdf:
            for xref in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(xref)
                    if any(action in obj for action in suspicious_actions):
                        has_suspicious_actions = 1
                        break
                except Exception as e:
                    logging.debug(f"Error processing object {xref} in {file_path}: {e}")
                    continue
        features['has_suspicious_actions'] = has_suspicious_actions

        # Feature 3: Number of Embedded Files
        num_embedded_files = 0
        if doc.is_pdf:
            try:
                num_embedded_files = len(doc.embeddedFileNames())
            except Exception as e:
                logging.debug(f"Error retrieving embedded files in {file_path}: {e}")
        features['num_embedded_files'] = num_embedded_files

        # Feature 4: Number of External URLs
        num_external_urls = 0
        url_pattern = re.compile(rb'(https?://[^\s<>\"\'()]+|www\.[^\s<>\"\'()]+)')
        if doc.is_pdf:
            for xref in range(1, doc.xref_length()):
                try:
                    stream = doc.xref_stream(xref)
                    if stream:
                        urls = url_pattern.findall(stream)
                        num_external_urls += len(urls)
                except Exception as e:
                    logging.debug(f"Error processing stream {xref} in {file_path}: {e}")
                    continue
        features['num_external_urls'] = num_external_urls

        # Feature 5: Presence of Obfuscated Streams
        # Check for compressed object streams or encrypted content
        has_obfuscated_streams = 0
        if doc.is_pdf:
            for xref in range(1, doc.xref_length()):
                try:
                    obj = doc.xref_object(xref)
                    if '/Filter' in obj and ('/FlateDecode' in obj or '/LZWDecode' in obj or '/ASCII85Decode' in obj):
                        has_obfuscated_streams = 1
                        break
                except Exception as e:
                    logging.debug(f"Error processing object {xref} in {file_path}: {e}")
                    continue
        features['has_obfuscated_streams'] = has_obfuscated_streams

        # Close the document to free up resources
        doc.close()
        features['file_name'] = os.path.basename(file_path)
        return features

    except Exception as e:
        logging.error(f"Error processing {file_path}: {type(e).__name__}: {e}")
        # Delete the file if it fails processing
        try:
            os.remove(file_path)
            logging.warning(f"Deleted file due to processing failure: {file_path}")
        except Exception as delete_error:
            logging.error(f"Failed to delete file {file_path}: {type(delete_error).__name__}: {delete_error}")

    # If an error occurs, initialize features to 0
    features = {
        'file_name': os.path.basename(file_path),
        'num_javascript': 0,
        'javascript_total_size': 0,
        'has_suspicious_actions': 0,
        'num_embedded_files': 0,
        'num_external_urls': 0,
        'has_obfuscated_streams': 0,
    }
    return features

async def process_pdfs(folder_path, label):
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    data = []

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = [
            loop.run_in_executor(executor, asyncio.run, extract_pdf_features(os.path.join(folder_path, filename)))
            for filename in pdf_files
        ]
        for response in await asyncio.gather(*tasks):
            features = response
            features['label'] = label
            data.append(features)
            logging.info(f"Completed processing for {features['file_name']}")
    return data

async def main(folder_path, label, output_file):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info(f"Starting PDF feature extraction in folder: {folder_path}")

    data = await process_pdfs(folder_path, label=label)

    df = pd.DataFrame(data)

    # Save to CSV
    async with aiofiles.open(output_file, mode='w') as f:
        await f.write(df.to_csv(index=False))
    logging.info(f"Feature extraction completed. Features saved to {output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PDF Feature Extraction Script')
    parser.add_argument('--folder', required=True, help='Path to folder containing PDFs')
    parser.add_argument('--label', type=int, required=True, help='Label for the PDFs (e.g., 0 for clean, 1 for malicious)')
    parser.add_argument('--output_file', default='pdf_features.csv', help='Output CSV file for extracted features')
    args = parser.parse_args()

    asyncio.run(main(args.folder, args.label, args.output_file))