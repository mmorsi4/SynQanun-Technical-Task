from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import RGBColor
from datetime import datetime
import re
import os

def extract_numeric(text):
    """
    helper function to extract numbers from text
    """
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None

def normalize_date_iso(value, format):
    """
    helper function to change dates to YYYY-MM-DD for postgres
    """
    value = value.strip()

    try:
        return datetime.strptime(value, format).strftime("%Y-%m-%d")
    except ValueError:
        return None

    return None

def parse_docx_file(file_path, doc_type):
    """
    main docx parser
    """
    document = Document(file_path)

    # for debugging and analysis
    # print(document._element.xml)

    title = "" # title/main header info, inferred from style in judgments/fatwas
    build_law_title = True # bool to keep building titles until first blue text in laws
    header_text_pairs = {} # header/text for sections
    current_header = None # to keep track of last header
    current_subheader = None # to keep track of last subheader
    size, color = None, None # text size/test color

    for paragraph in document.paragraphs:
        if not paragraph.text.strip():
            continue

        if not paragraph.runs:
            continue

        if paragraph.runs:
            size, color = paragraph.runs[0].font.size, paragraph.runs[0].font.color.rgb        

        # parsing based on doc_type
        if doc_type == "judgment":
            if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER: # centered text is a title
                title = paragraph.text if not title else title + " " + paragraph.text
                continue
            if size == 177800: # header
                current_header = paragraph.text
                header_text_pairs[current_header] = {}
                current_subheader = None
            elif size == 152400:  # subheader
                if current_header is None:
                    continue
                num = extract_numeric(paragraph.text)
                if num is not None:
                    current_subheader = num
                    header_text_pairs[current_header][current_subheader] = ""
            else: # body
                if current_header and current_subheader:
                    header_text_pairs[current_header][current_subheader] += " " + paragraph.text
                elif current_header:
                    header_text_pairs[current_header] = paragraph.text

        elif doc_type == "fatwa":
            if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER: # centered text is a title
                title = paragraph.text if not title else title + " " + paragraph.text
                continue
            if size == 177800: # header
                current_header = paragraph.text
                num = extract_numeric(paragraph.text)
                if num is not None:
                    current_header = num
                header_text_pairs[current_header] = ""
            else: # body
                header_text_pairs[current_header] = paragraph.text

        elif doc_type == "law":
            if not current_header and color == RGBColor(0, 0, 255): # build title until first blue text
                build_law_title = False
                continue

            if build_law_title: # keep building title
                title = paragraph.text if not title else title + " " + paragraph.text

            else:
                # since headers/subheaders are not stylized in laws
                # use regex to extract them
                header_match = re.match(
                    r"^المادة\s+(?P<number>\d+)(?:\s+(?P<type>اصدار|مكرر))?$",
                    paragraph.text
                )

                if header_match:
                    current_subheader = int(header_match.group("number"))
                    article_type = header_match.group("type")
                    repeated = True if article_type == "مكرر" else False

                    if article_type == "اصدار":
                        current_header = "promulgation_articles"
                    else:
                        current_header = "articles"

                    if current_header not in header_text_pairs:
                        header_text_pairs[current_header] = {}

                    if repeated:
                        current_subheader = str(current_subheader) + "_repeated"

                    header_text_pairs[current_header][current_subheader] = {}

                    if repeated:
                        header_text_pairs[current_header][current_subheader]["repeated"] = True

                elif not current_header or not current_subheader:
                    continue

                elif paragraph.runs[0].font.color.rgb == RGBColor(0, 0, 255): # blue text is the final text date
                    final_text_date_pattern = re.compile(r"\s+(?P<final_text_date>[\d/-]+)")
                    match = final_text_date_pattern.search(paragraph.text)
                    if match:
                        header_text_pairs[current_header][current_subheader]["final_text_date"] = normalize_date_iso(match.group("final_text_date"), "%d/%m/%Y")

                elif paragraph.runs[0].font.color.rgb == RGBColor(128, 128, 128): # gray is the original text
                    content = paragraph.text
                    if "النص الاصلى للمادة\n" in content:
                        content = content.replace("النص الاصلى للمادة\n", "")
                    if content:
                        prev = header_text_pairs[current_header][current_subheader].get("original_text", "")
                        header_text_pairs[current_header][current_subheader]["original_text"] = (prev + " " + content).strip()

                else: # black text is the final text
                    content = paragraph.text
                    if content:
                        prev = header_text_pairs[current_header][current_subheader].get("final_text", "")
                        header_text_pairs[current_header][current_subheader]["final_text"] = (prev + " " + content).strip()

    # information extraction from title using regex
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
        patterns = {
            "law_number": re.compile(r"قانون\s+-\s+رقم\s+(?P<law_number>\d+)"),
            "issue_date": re.compile(r"الصادر\s+بتاريخ\s+(?P<issue_date>[\d-]+)"),
            "publish_date": re.compile(r"نشر\s+بتاريخ\s+(?P<publish_date>[\d-]+)"),
            "effective_date": re.compile(r"يعمل\s+به\s+اعتبارا\s+من\s+(?P<effective_date>[\d-]+)"),
            "subject": re.compile(r"بشأن\s+(?P<subject>.+?)\s+الجريدة\s+الرسمية"),
            "gazette": re.compile(r"الجريدة\s+الرسمية\s+(?P<gazette>.+)")
        }
        section_key_mapping = {} # headers/subheaders are not unique in style so this is not used, we use regex directly

    # extract regex fields
    for key, pat in patterns.items():
        m = pat.search(title)
        if m:
            regex_result[key] = m.group(key)

    # map Arabic headers to English keys
    for key in list(header_text_pairs.keys()):
        if key in section_key_mapping:
            header_text_pairs[section_key_mapping[key]] = header_text_pairs.pop(key)

    # for judgments, remove the spaces in 'hearing_date'
    if doc_type == "judgment":
        regex_result["hearing_date"] = normalize_date_iso(regex_result["hearing_date"].replace(" ", ""), "%d/%m/%Y")

    # for fatwas, move numeric headers under 'principles' key
    if doc_type == "fatwa":
        principles_dict = {}
        for key in list(header_text_pairs.keys()):
            if isinstance(key, int):
                principles_dict[key] = header_text_pairs.pop(key)
        if principles_dict:
            header_text_pairs["principles"] = principles_dict

    # combine everything and return the final result
    final_result = {"doc_type": doc_type, "file_name": file_path.split("/")[-1]} | regex_result | header_text_pairs
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
        res = parse_docx_file(file_path, doc_type)
        results.append(res)
    return results