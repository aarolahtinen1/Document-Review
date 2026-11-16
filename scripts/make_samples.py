"""Build samples/services-agreement.docx from samples/services-agreement.txt."""
from pathlib import Path

import docx

root = Path(__file__).resolve().parent.parent / "samples"
text = (root / "services-agreement.txt").read_text()

d = docx.Document()
for line in text.splitlines():
    if line.strip():
        d.add_paragraph(line)
d.save(root / "services-agreement.docx")
print("wrote", root / "services-agreement.docx")
