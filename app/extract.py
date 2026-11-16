"""Turn an uploaded contract (.docx or .pdf) into numbered paragraphs for Claude.

Both formats are reduced to plain text paragraphs. That keeps PDFs as cheap as
Word documents (Claude would otherwise read a PDF as text plus an image of every
page) and lets the review screen highlight quotes the same way for both.
Scanned PDFs (no text layer) are rejected.
"""

import io
import re
import statistics
import unicodedata
from dataclasses import dataclass

import docx
from docx.table import Table
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_UPLOAD_BYTES = 30 * 1024 * 1024


class InputError(ValueError):
    """The upload can't be reviewed; message is shown to the user."""


@dataclass
class PreparedInput:
    content_block: dict
    source_name: str
    paragraphs: list[str]  # document text in reading order; index + 1 = the [n] number Claude sees

    @property
    def source_text(self) -> str:
        return "\n".join(self.paragraphs)


def from_upload(filename: str, data: bytes) -> PreparedInput:
    name = filename or "document"
    lower = name.lower()
    if not (lower.endswith(".docx") or lower.endswith(".pdf")):
        raise InputError("Upload the contract as a PDF or Word document (.pdf or .docx).")
    if not data:
        raise InputError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise InputError("The file is larger than 30 MB.")

    if lower.endswith(".pdf"):
        paragraphs = _pdf_paragraphs(data)
    else:
        try:
            paragraphs = _docx_paragraphs(data)
        except Exception as e:  # python-docx raises assorted zip/XML/package errors for bad files
            raise InputError("Could not read the file as a Word document. Check it is a valid .docx (not .doc).") from e
        if not paragraphs:
            raise InputError("The Word document contains no text.")

    # Number paragraphs so Claude can say where each quote comes from.
    numbered = "\n".join(f"[{i}] {p}" for i, p in enumerate(paragraphs, start=1))
    return PreparedInput(
        content_block={
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": numbered},
            "title": name,
        },
        source_name=name,
        paragraphs=paragraphs,
    )


# ---------- Word ----------

def _docx_paragraphs(data: bytes) -> list[str]:
    """Paragraphs and table rows in reading order, empty lines dropped."""
    d = docx.Document(io.BytesIO(data))
    out: list[str] = []
    for block in d.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                cells = _unique_cells(row)
                if any(cells):
                    out.append(" | ".join(cells))
        elif block.text.strip():
            out.append(block.text.strip())
    return out


def _unique_cells(row) -> list[str]:
    # Merged cells repeat the same cell object across the row; keep each once.
    seen, cells = set(), []
    for c in row.cells:
        if id(c._tc) not in seen:
            seen.add(id(c._tc))
            cells.append(c.text.strip())
    return cells


# ---------- PDF ----------

# A line that starts a new clause: "1.", "1.1", "12.3.4", "(a)", "(iv)", "Clause 5", "Schedule 1".
_CLAUSE_START = re.compile(r"^(\d+(\.\d+)*\.?\s|\(?[a-z]{1,4}\)\s|\(\d{1,3}\)\s|(clause|schedule|annex(ure)?|appendix|part)\s+\w+)", re.I)
# Standalone page numbers: "3", "Page 3", "3 of 10", "Page 3 of 10", "- 3 -".
_PAGE_NUMBER = re.compile(r"^[-–\s]*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?[-–\s]*$", re.I)


def _pdf_paragraphs(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF-"):
        raise InputError("Could not read the file as a PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise InputError("This PDF is password-protected. Remove the password and upload it again.")
        # NFKC turns typographic ligatures ("ﬁ", "ﬂ") and odd spaces back into plain characters.
        pages = [unicodedata.normalize("NFKC", page.extract_text() or "") for page in reader.pages]
    except InputError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as e:
        raise InputError("Could not read the file as a PDF.") from e

    text_chars = sum(len(p.strip()) for p in pages)
    if text_chars < 40 * max(1, len(pages)):
        raise InputError(
            "This PDF has little or no selectable text. It's probably a scan. "
            "Upload a text-based PDF or a Word document instead."
        )

    lines = [ln.strip() for page in pages for ln in page.splitlines()]
    content = [ln for ln in lines if ln]
    # Typical full line length, used to spot short lines that end a paragraph.
    full_line = statistics.quantiles([len(ln) for ln in content], n=4)[2] if len(content) >= 4 else 80

    paragraphs: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            paragraphs.append(_join_lines(buf))
            buf.clear()

    for line in lines:
        if not line:
            flush()
            continue
        if _PAGE_NUMBER.match(line):
            continue
        is_heading = line.isupper() and len(line) <= 80 and any(c.isalpha() for c in line)
        if buf and (_CLAUSE_START.match(line) or is_heading):
            flush()
        buf.append(line)
        # A heading, or a short line ending a sentence, closes the paragraph.
        if is_heading or (line[-1] in ".:;" and len(line) < 0.85 * full_line):
            flush()
    flush()
    return paragraphs


def _join_lines(lines: list[str]) -> str:
    out = lines[0]
    for ln in lines[1:]:
        if out.endswith("-") and ln[:1].islower():
            out = out[:-1] + ln  # re-join a word hyphenated across lines
        else:
            out += " " + ln
    return re.sub(r"\s+", " ", out).strip()
