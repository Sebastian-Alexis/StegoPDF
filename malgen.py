import os
import json
import PyPDF2
from PyPDF2.generic import DictionaryObject, NameObject, create_string_object, StreamObject, ArrayObject, NumberObject
import random
import asyncio
from tqdm import tqdm

# Paths to folders
CLEAN_FOLDER = 'clean'
DIRTY_FOLDER = 'dirty'
LOG_FILE = 'injection_log.json'

# Features to inject (script type and behavior, object streams, structure anomalies, acroform usage)
FEATURES = ['script_behavior', 'suspicious_object_streams', 'document_structure_anomalies', 'acroform_xfa_usage']

# Load or create log file
def load_log():
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
        with open(LOG_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

# Save log file
def save_log(log_data):
    with open(LOG_FILE, 'w') as file:
        json.dump(log_data, file, indent=4)

# Inject JavaScript (script type and behavior)
def inject_script_behavior(pdf_writer):
    js_variants = [
        "eval(String.fromCharCode(72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33));",  # Obfuscated Hello World
        "app.alert({cMsg: \"Hello, World!\", nIcon: 3});",  # Custom alert with icon
        "var docTitle = this.documentFileName; if (docTitle) app.alert(\"Hello, World!\");",  # Conditional JavaScript
        "try { console.show(); console.println(\"Hello, World!\"); } catch (e) { app.alert(\"Console failed\"); }",  # Attempting to use console
        "app.setInterval(\"app.alert('Hello, World!');\", 5000);",  # Repeated alerts with setInterval
        "function sayHello() { app.alert(\"Hello, World!\"); } sayHello();",  # Function definition and call
        "var userResponse = app.response(\"Enter something:\"); app.alert(\"You entered: \" + userResponse);",  # Using user input
        "app.launchURL(\"http://example.com\"); app.alert(\"Hello, World!\");",  # Launch URL followed by alert
        "var a = []; a.push(\"Hello\"); a.push(\"World\"); app.alert(a.join(\", \"));",  # Array manipulation
        "app.alert(unescape(\"%48%65%6C%6C%6F%2C%20%57%6F%72%6C%64%21\"));"  # Using unescape for Hello World
    ]
    js_code = random.choice(js_variants)
    js_action = PyPDF2.generic.DictionaryObject()
    js_action.update({
        NameObject("/S"): NameObject("/JavaScript"),
        NameObject("/JS"): create_string_object(js_code)
    })
    pdf_writer.add_js(js_action)

# Inject suspicious object streams
def inject_object_streams(pdf_writer):
    # Create a dummy executable file
    dummy_exe_content = b"This is a dummy executable for testing purposes."
    stream = StreamObject()
    stream._data = dummy_exe_content
    stream.update({
        NameObject("/Type"): NameObject("/EmbeddedFile"),
        NameObject("/Subtype"): NameObject("/application/octet-stream"),
        NameObject("/Params"): DictionaryObject({
            NameObject("/Size"): NumberObject(len(dummy_exe_content)),
            NameObject("/CheckSum"): create_string_object("1234567890abcdef")  # Dummy checksum
        })
    })
    pdf_writer._root_object.update({
        NameObject(f"/HiddenStream_{random.randint(1000, 9999)}"): stream
    })

# Inject document structure anomalies
def inject_structure_anomalies(pdf_writer):
    pdf_writer._root_object.update({
        NameObject("/HiddenObject"): create_string_object("This is a hidden object that shouldn't be here.")
    })

# Inject AcroForm and XFA form
def inject_acroform_xfa(pdf_writer):
    acroform_variants = [
        {  # Basic AcroForm with dummy fields
            NameObject("/Fields"): ArrayObject([DictionaryObject({
                NameObject("/FT"): NameObject("/Tx"),
                NameObject("/T"): create_string_object("DummyField"),
                NameObject("/V"): create_string_object("Suspicious Value")
            })]),
            NameObject("/DA"): create_string_object("/Helv 0 Tf 0 g")
        },
        {  # XFA Form variant
            NameObject("/XFA"): create_string_object("<xdp:xdp xmlns:xdp=\"http://ns.adobe.com/xdp/\"><template><subform name=\"form1\"><field name=\"field1\"><value><text>Suspicious Value</text></value></field></subform></template></xdp:xdp>")
        },
        {  # AcroForm with hidden actions
            NameObject("/Fields"): ArrayObject([DictionaryObject({
                NameObject("/FT"): NameObject("/Tx"),
                NameObject("/T"): create_string_object("HiddenField"),
                NameObject("/AA"): DictionaryObject({
                    NameObject("/K"): DictionaryObject({
                        NameObject("/S"): NameObject("/JavaScript"),
                        NameObject("/JS"): create_string_object("app.alert('Hidden Action Executed');")
                    })
                })
            })]),
            NameObject("/DA"): create_string_object("/Helv 0 Tf 0 g")
        }
    ]
    acroform = random.choice(acroform_variants)
    pdf_writer._root_object.update({NameObject("/AcroForm"): DictionaryObject(acroform)})

# Asynchronous function to process a single PDF file
async def process_file(filename, log_data):
    clean_pdf_path = os.path.join(CLEAN_FOLDER, filename)
    if clean_pdf_path not in log_data:
        log_data[clean_pdf_path] = []
        save_log(log_data)

    # Skip if all features have already been injected
    if len(log_data[clean_pdf_path]) == len(FEATURES):
        return

    # Open the clean PDF and create a new "dirty" version
    with open(clean_pdf_path, 'rb') as clean_file:
        try:
            reader = PyPDF2.PdfReader(clean_file, strict=False)
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            return

        pdf_writer = PyPDF2.PdfWriter()

        for page_num in range(len(reader.pages)):
            try:
                pdf_writer.add_page(reader.pages[page_num])
            except Exception as e:
                print(f"Error adding page {page_num} in file {filename}: {e}")
                continue

        # Inject features that have not yet been applied to this PDF
        for feature in FEATURES:
            if feature not in log_data[clean_pdf_path]:
                try:
                    if feature == 'script_behavior':
                        inject_script_behavior(pdf_writer)
                    elif feature == 'suspicious_object_streams':
                        inject_object_streams(pdf_writer)
                    elif feature == 'document_structure_anomalies':
                        inject_structure_anomalies(pdf_writer)
                    elif feature == 'acroform_xfa_usage':
                        inject_acroform_xfa(pdf_writer)

                    # Save the dirty PDF
                    dirty_pdf_path = os.path.join(DIRTY_FOLDER, f'dirty_{filename}_{feature}.pdf')
                    with open(dirty_pdf_path, 'wb') as dirty_file:
                        pdf_writer.write(dirty_file)

                    # Update log
                    log_data[clean_pdf_path].append(feature)
                    save_log(log_data)
                    break
                except Exception as e:
                    print(f"Error injecting feature '{feature}' in file {filename}: {e}")
                    continue

# Asynchronous function to process all PDF files
async def process_files():
    log_data = load_log()
    filenames = [f for f in os.listdir(CLEAN_FOLDER) if f.endswith('.pdf')]

    for filename in tqdm(filenames, desc="Processing PDF files"):
        await process_file(filename, log_data)

if __name__ == "__main__":
    if not os.path.exists(DIRTY_FOLDER):
        os.makedirs(DIRTY_FOLDER)
    asyncio.run(process_files())
