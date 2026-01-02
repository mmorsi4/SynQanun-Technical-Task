from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re

JUDGEMENT_DIR = "./example-samples/judgments/"
document = Document(JUDGEMENT_DIR + 'judgment1.docx')

# print(document._element.xml)

title = ""
header_text_pairs = {}
current_header = None
current_subheader = None

for paragraph in document.paragraphs:
    if not paragraph.text.strip():
        continue

    if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
        title += " " + paragraph.text
        continue