"""Build .docx and .pdf versions of samples/services-agreement.txt."""
import html
from pathlib import Path

import docx
from weasyprint import HTML

root = Path(__file__).resolve().parent.parent / "samples"
text = (root / "services-agreement.txt").read_text()
lines = text.splitlines()

d = docx.Document()
for line in lines:
    if line.strip():
        d.add_paragraph(line)
d.save(root / "services-agreement.docx")

body = "".join(f"<p>{html.escape(l)}</p>" if l.strip() else "" for l in lines)
HTML(string=f"<html><body style='font-family:Times;font-size:11pt'>{body}</body></html>").write_pdf(
    root / "services-agreement.pdf"
)
print("wrote", root / "services-agreement.docx", root / "services-agreement.pdf")
