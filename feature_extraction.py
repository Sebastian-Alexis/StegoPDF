import os
import argparse
import pandas as pd
from PyPDF2 import PdfReader
import numpy as np
import logging

def extract_pdf_features(file_path):
    features = {}
    try:
        # Initialize reader
        reader = PdfReader(file_path)

        # Feature 1: Presence of JavaScript
        has_javascript = 0
        for page in reader.pages:
            if '/Annots' in page:
                annotations = page['/Annots']
                for annot in annotations:
                    annot_obj = annot.get_object()
                    if '/A' in annot_obj:
                        action = annot_obj['/A']
                        if '/S' in action and action['/S'] == '/JavaScript':
                            has_javascript = 1
                            break
                    if '/AA' in annot_obj:
                        additional_actions = annot_obj['/AA']
                        if '/S' in additional_actions and additional_actions['/S'] == '/JavaScript':
                            has_javascript = 1
                            break
        features['has_javascript'] = has_javascript

        # Feature 2: Number of Embedded Files
        num_embedded_files = 0
        if '/Names' in reader.trailer['/Root']:
            names = reader.trailer['/Root']['/Names'].get_object()
            if '/EmbeddedFiles' in names:
                embedded_files = names['/EmbeddedFiles']['/Names']
                num_embedded_files = len(embedded_files) // 2  # Names are in pairs: key and value
        features['num_embedded_files'] = num_embedded_files

        # Feature 3: Presence of Launch Actions
        has_launch = 0
        for page in reader.pages:
            if '/Annots' in page:
                annotations = page['/Annots']
                for annot in annotations:
                    annot_obj = annot.get_object()
                    if '/A' in annot_obj:
                        action = annot_obj['/A']
                        if '/S' in action and action['/S'] == '/Launch':
                            has_launch = 1
                            break
        features['has_launch'] = has_launch

        # Feature 4: Missing Metadata Fields
        metadata = reader.metadata
        missing_metadata_fields = 0
        standard_fields = ['/Author', '/Creator', '/Producer', '/Title', '/Subject', '/Keywords', '/CreationDate', '/ModDate']
        for field in standard_fields:
            if getattr(metadata, field[1:], None) is None:
                missing_metadata_fields += 1
        features['missing_metadata_fields'] = missing_metadata_fields

        # Feature 5: Number of Annotations
        num_annotations = 0
        for page in reader.pages:
            if '/Annots' in page:
                annotations = page['/Annots']
                num_annotations += len(annotations)
        features['num_annotations'] = num_annotations

        # Feature 6: Encryption Flag
        features['is_encrypted'] = int(reader.is_encrypted)

        # Feature 7: Number of Pages
        features['num_pages'] = len(reader.pages)

        # Feature 8: File Size (in KB)
        file_size = os.path.getsize(file_path) / 1024.0  # Convert bytes to kilobytes
        features['file_size_kb'] = file_size

        # Feature 9: PDF Version
        pdf_version = reader.pdf_header_version
        features['pdf_version'] = float(pdf_version)

        # Feature 10: Number of Images
        num_images = 0
        for page in reader.pages:
            if '/Resources' in page:
                resources = page['/Resources']
                if '/XObject' in resources:
                    xobjects = resources['/XObject']
                    for obj in xobjects.values():
                        xobj = obj.get_object()
                        if '/Subtype' in xobj and xobj['/Subtype'] == '/Image':
                            num_images += 1
        features['num_images'] = num_images

        # Add more features as needed

    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")
        # Initialize features to NaN
        features = {
            'has_javascript': np.nan,
            'num_embedded_files': np.nan,
            'has_launch': np.nan,
            'missing_metadata_fields': np.nan,
            'num_annotations': np.nan,
            'is_encrypted': np.nan,
            'num_pages': np.nan,
            'file_size_kb': np.nan,
            'pdf_version': np.nan,
            'num_images': np.nan,
            # Add more features as needed
        }
    return features

def process_pdfs(folder_path, label):
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    data = []
    for file_path in pdf_files:
        features = extract_pdf_features(file_path)
        features['label'] = label
        features['file_name'] = os.path.basename(file_path)
        data.append(features)
        logging.info(f"Processed {file_path}")
    return data

def main(clean_folder, dirty_folder, output_file):
    logging.basicConfig(level=logging.INFO)

    logging.info("Processing clean PDFs...")
    clean_data = process_pdfs(clean_folder, label=0)

    logging.info("Processing dirty PDFs...")
    dirty_data = process_pdfs(dirty_folder, label=1)

    all_data = clean_data + dirty_data
    df = pd.DataFrame(all_data)

    # Save to CSV
    df.to_csv(output_file, index=False)
    logging.info(f"Features saved to {output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PDF Feature Extraction Script')
    parser.add_argument('--clean_folder', required=True, help='Path to folder containing clean PDFs')
    parser.add_argument('--dirty_folder', required=True, help='Path to folder containing dirty PDFs')
    parser.add_argument('--output_file', default='pdf_features.csv', help='Output CSV file for extracted features')
    args = parser.parse_args()

    main(args.clean_folder, args.dirty_folder, args.output_file)


#python feature_extraction.py --clean_folder path/to/clean --dirty_folder path/to/dirty --output_file pdf_features.csv