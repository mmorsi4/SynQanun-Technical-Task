from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os

JUDGMENT_DIR = "./example-samples/judgments/"
FATWA_DIR = "./example-samples/fatwas/"
LAW_DIR = "./example-samples/laws/"

def extract_numeric(text):
    """
    helper function to extract numbers from text
    """
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None

def parse_docx_file(filename, file_path, doc_type):
    """
    main docx parser
    """
    document = Document(file_path)

    title = ""
    header_text_pairs = {}
    current_header = None
    current_subheader = None

    for paragraph in document.paragraphs:
        if not paragraph.text.strip():
            continue

        if not paragraph.runs:
            continue

        size = paragraph.runs[0].font.size if paragraph.runs else None

        # Parsing based on doc_type
        if doc_type == "judgment":  # judgments and laws may have headers/subheaders
            if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
                title = paragraph.text if not title else title + " " + paragraph.text
                continue
            if size == 177800:  # header
                current_header = paragraph.text
                header_text_pairs[current_header] = {}
                current_subheader = None
            elif size == 152400:  # subheader (numeric)
                if current_header is None:
                    continue
                num = extract_numeric(paragraph.text)
                if num is not None:
                    current_subheader = num
                    header_text_pairs[current_header][current_subheader] = ""
            else:  # body
                if current_header and current_subheader:
                    header_text_pairs[current_header][current_subheader] += " " + paragraph.text
                elif current_header:
                    header_text_pairs[current_header] = paragraph.text

        elif doc_type == "fatwa":
            # Fatwa logic
            if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
                title = paragraph.text if not title else title + " " + paragraph.text
                continue
            if size == 177800:  # header
                current_header = paragraph.text
                num = extract_numeric(paragraph.text)
                if num is not None:
                    current_header = num
                header_text_pairs[current_header] = ""
            else:  # body
                header_text_pairs[current_header] = paragraph.text

        elif doc_type == "law":
            if size == 177800:  # header
                current_header = paragraph.text
                num = extract_numeric(paragraph.text)
                if num is not None:
                    current_header = num
                header_text_pairs[current_header] = ""
            else:  # body
                header_text_pairs[current_header] = paragraph.text

    # Regex extraction
    regex_result = {}
    if doc_type == "judgment":
        patterns = {
            "court_name": re.compile(r"جمهورية\s*مصر\s*العربية\s*-\s*(?P<court_name>.+?)\s*-\s*(?P<chamber_type>\w+)"),
            "chamber_type": re.compile(r"محكمة\s*النقض\s+-\s+(?P<chamber_type>\w+)"),
            "appeal_number": re.compile(r"الطعن\s+رقم\s+(?P<appeal_number>\d+)"),
            "judicial_year": re.compile(r"ل\s*سنة\s+(?P<judicial_year>\d+)"),
            "hearing_date": re.compile(r"تاريخ\s+الجلسة\s*:?\s*(?P<hearing_date>[\d\s/]+)"),
            "volume_number": re.compile(r"مكتب\s+فني\s+(?P<volume_number>\d+)"),
            "part_number": re.compile(r"رقم\s+الجزء\s+(?P<part_number>\d+)"),
            "page_number": re.compile(r"رقم\s+الصفحة\s+(?P<page_number>\d+)"),
            "rule_number": re.compile(r"القاعدة\s+رقم\s+(?P<rule_number>\d+)"),
            "reference_number": re.compile(r"الرقم\s+المرجعي\s*:\s*(?P<reference_number>\d+)"),
        }
        section_key_mapping = {
            "الهيئة": "authority",
            "المبادئ القانونية": "principles",
            "الوقائع": "facts",
            "الحيثيات": "reasons"
        }

    elif doc_type == "fatwa":
        patterns = {
            "fatwa_number": re.compile(r"\s+الفتوى\s+رقم\s+(?P<fatwa_number>\d+)"),
            "file_number": re.compile(r"\s+رقم\s+الملف\s+(?P<file_number>[\d/-]+)"),
            "fatwa_date": re.compile(r"\s+?بتاريخ\s+(?P<fatwa_date>[\d/-]+)"),
            "hearing_date": re.compile(r"\s+تاريخ\s+الجلسة\s+(?P<hearing_date>[\d/-]+)")
        }
        section_key_mapping = {
            "الجهة": "authority",
            "موضوع الفتوى": "topic",
            "الوقائع": "facts",
            "التطبيق": "application",
            "الرأى": "opinion"
        }

    elif doc_type == "law":
        # Placeholder for future laws parsing
        patterns = {}
        section_key_mapping = {}

    # Extract regex fields
    for key, pat in patterns.items():
        m = pat.search(title)
        if m:
            regex_result[key] = m.group(key)

    # Map Arabic headers to English keys
    for key in list(header_text_pairs.keys()):
        if key in section_key_mapping:
            header_text_pairs[section_key_mapping[key]] = header_text_pairs.pop(key)

    # For fatwas, move numeric headers under 'principles'
    if doc_type == "fatwa":
        principles_dict = {}
        for key in list(header_text_pairs.keys()):
            if isinstance(key, int):
                principles_dict[key] = header_text_pairs.pop(key)
        if principles_dict:
            header_text_pairs["principles"] = principles_dict

    # Combine everything
    final_result = {"doc_type": doc_type, "file_name": filename} | regex_result | header_text_pairs
    return final_result

def parse_directory(dir_path, doc_type):
    """
    run the docx parser over an entire directory
    """
    results = []
    for filename in os.listdir(dir_path):
        if not filename.endswith(".docx") or filename.startswith("~$"):
            continue
        file_path = os.path.join(dir_path, filename)
        res = parse_docx_file(filename, file_path, doc_type)
        results.append(res)
    return results

# Parse all document types
all_judgments = parse_directory(JUDGMENT_DIR, "judgment")
all_fatwas = parse_directory(FATWA_DIR, "fatwa")
all_laws = parse_directory(LAW_DIR, "law")  # placeholder

# Combine all results
all_documents = all_judgments + all_fatwas + all_laws

# Example: print top-level keys of each document
for i, doc in enumerate(all_documents, 1):
    print(f"Document {i} ({doc['doc_type'], {doc['file_name']}}):", list(doc.keys()))