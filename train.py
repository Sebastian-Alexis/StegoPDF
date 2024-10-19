import os
import json
import numpy as np
import hashlib
from sklearn.svm import SVC
from tqdm import tqdm
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
import fitz  # PyMuPDF
import PyPDF2

# Paths to folders and JSON file
CLEAN_FOLDER = 'clean'
DIRTY_FOLDER = 'dirty'
METADATA_JSON_PATH = 'injection_log.json'
CACHE_FILE_PATH = 'feature_cache.json'

# Function to generate a hash for a file
def generate_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

# Function to load cache from file
def load_cache():
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, 'r') as cache_file:
            return json.load(cache_file)
    return {}

# Function to save cache to file
def save_cache(cache):
    with open(CACHE_FILE_PATH, 'w') as cache_file:
        json.dump(cache, cache_file)

# Function to extract JavaScript using PyMuPDF
def extract_javascript_with_pymupdf(pdf_path):
    try:
        document = fitz.open(pdf_path)
        for page_number in range(len(document)):
            page = document.load_page(page_number)
            annot = page.first_annot
            while annot:
                if annot.type[0] == 21:  # Check if annotation is JavaScript
                    return 1  # JavaScript found
                annot = annot.next
        document.close()
    except Exception as e:
        print(f"An error occurred with PyMuPDF: {e}")
    return 0

# Function to extract JavaScript using PyPDF2
def extract_javascript_with_pypdf2(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            if "/Names" in reader.trailer["/Root"]:
                names = reader.trailer["/Root"]["/Names"]
                if "/JavaScript" in names:
                    js_dict = names["/JavaScript"]["/Names"]
                    for i in range(1, len(js_dict), 2):
                        javascript = js_dict[i].get_object()
                        if javascript.get("/JS"):
                            return 1  # JavaScript found
    except Exception as e:
        print(f"An error occurred with PyPDF2: {e}")
    return 0

# Function to extract JSON features from a PDF file
def extract_json_features_from_pdf(pdf_path):
    pymupdf_result = extract_javascript_with_pymupdf(pdf_path)
    pypdf2_result = extract_javascript_with_pypdf2(pdf_path)
    if pymupdf_result or pypdf2_result:
        print(f"JavaScript found in {pdf_path}")
    return 1 if pymupdf_result or pypdf2_result else 0

# Function to create feature matrix from PDFs
def create_feature_matrix(folder, metadata, cache):
    pdf_files = [f for f in os.listdir(folder) if f.endswith('.pdf')]
    features = []

    for pdf_file in tqdm(pdf_files, desc=f"Extracting features from {folder}"):
        pdf_path = os.path.join(folder, pdf_file)
        file_hash = generate_file_hash(pdf_path)

        # Check if features are in cache
        if file_hash in cache:
            json_features = cache[file_hash]['json_features']
        else:
            # Extract features from the PDF itself
            script_behavior = extract_json_features_from_pdf(pdf_path)
            suspicious_object_streams = 1 if "suspicious_object_streams" in metadata.get(f"{folder}/{pdf_file}", []) else 0
            document_structure_anomalies = 1 if "document_structure_anomalies" in metadata.get(f"{folder}/{pdf_file}", []) else 0
            acroform_xfa_usage = 1 if "acroform_xfa_usage" in metadata.get(f"{folder}/{pdf_file}", []) else 0

            json_features = [script_behavior, suspicious_object_streams, document_structure_anomalies, acroform_xfa_usage]
            cache[file_hash] = {'json_features': json_features}

        features.append(json_features)
    
    return np.array(features)

if __name__ == "__main__":
    # Load metadata from JSON file
    with open(METADATA_JSON_PATH, 'r') as json_file:
        metadata = json.load(json_file)

    # Load feature cache
    cache = load_cache()

    # Extract features for clean and dirty PDFs
    print("Extracting features for clean PDFs...")
    clean_features = create_feature_matrix(CLEAN_FOLDER, metadata, cache)
    print("Extracting features for dirty PDFs...")
    dirty_features = create_feature_matrix(DIRTY_FOLDER, metadata, cache)

    # Save updated cache
    save_cache(cache)

    # Combine features and create labels (0 for clean, 1 for dirty)
    X = np.vstack([clean_features, dirty_features])
    y = np.hstack([np.zeros(len(clean_features)), np.ones(len(dirty_features))])

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Fit Support Vector Classifier (SVM) model with cross-validation
    print("Fitting Support Vector Classifier (SVM) model with cross-validation...")
    model = SVC(kernel='linear', random_state=42)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_train, y_train, cv=skf, scoring='accuracy')
    print(f"Cross-Validation Accuracy Scores: {cv_scores}")
    print(f"Mean Cross-Validation Accuracy: {cv_scores.mean() * 100:.2f}%")

    # Train the model on the full training set
    model.fit(X_train, y_train)

    # Predict on the test set
    print("Predicting on the test set...")
    predictions = model.predict(X_test)

    # Evaluate the model
    accuracy = accuracy_score(y_test, predictions)
    print(f"Model accuracy: {accuracy * 100:.2f}%")
    print("Classification Report:")
    print(classification_report(y_test, predictions))
