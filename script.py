from docx import Document
import re

FATWA_DIR = "./example-samples/fatwas/"
document = Document(FATWA_DIR + 'fatwa3_2020.docx')

title = ""
header_text_pairs = {}

for paragraph in document.paragraphs:
    if paragraph.runs:
        if(paragraph.runs[0].font.size == 203200): # title
            title = paragraph.text

        elif(paragraph.runs[0].font.size == 177800): # header
            header_text_pairs[paragraph.text] = ""

        else: # paragraph of the last header inserted in the dictionary
            header_text_pairs[list(header_text_pairs.keys())[-1]] = paragraph.text

patterns = {
    "fatwa_number": re.compile(r"\s+الفتوى\s+رقم\s+(?P<fatwa_number>\d+)"),
    "file_number": re.compile(r"\s+رقم\s+الملف\s+(?P<file_number>[\d/-]+)"),
    "fatwa_date": re.compile(r"\s+?بتاريخ\s+(?P<fatwa_date>[\d/-]+)"),
    "session_date": re.compile(r"\s+تاريخ\s+الجلسة\s+(?P<session_date>[\d/-]+)")
}

result = {}
for key, pat in patterns.items():
    m = pat.search(title)
    if m:
        result[key] = m.group(key)

print(result)

# title 203200
# header 177800
# paragraph -> no run

# SCHEMA:

# fatwa id ??
# fatwa number
# fatwa date
# session date
# file number

# authority
# topic
# incidents
# application

# case
# opinion