"""Normalise user input into a Claude content block."""

import base64
import io
from dataclasses import dataclass

import docx

MAX_PDF_BYTES = 30 * 1024 * 1024  # API request limit is 32 MB; leave headroom for base64 + prompt


class InputError(ValueError):
    """The upload can't be reviewed; message is shown to the user."""


@dataclass
class PreparedInput:
    content_block: dict
    source_name: str
    source_text: str | None  # plain text when we have it (used for quote verification)


def from_upload(filename: str, data: bytes) -> PreparedInput:
    if not data:
        raise InputError("The uploaded file is empty.")
    name = filename or "document"
    lower = name.lower()

    if lower.endswith(".pdf") or data[:5] == b"%PDF-":
        if len(data) > MAX_PDF_BYTES:
            raise InputError("PDF is larger than 30 MB; please split it or upload a smaller file.")
        return PreparedInput(
            content_block={
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(data).decode("ascii"),
                },
                "title": name,
            },
            source_name=name,
            source_text=None,
        )

    if lower.endswith(".docx"):
        try:
            text = _docx_to_text(data)
        except Exception as e:  # python-docx raises a variety of zip/xml errors
            raise InputError(f"Could not read the .docx file: {e}") from e
        return from_text(text, name)

    raise InputError("Unsupported file type. Upload a .pdf or .docx, or paste the text.")


def from_text(text: str, source_name: str = "pasted-text") -> PreparedInput:
    text = (text or "").strip()
    if not text:
        raise InputError("No contract text was provided.")
    return PreparedInput(
        content_block={
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": text},
            "title": source_name,
        },
        source_name=source_name,
        source_text=text,
    )


def _docx_to_text(data: bytes) -> str:
    d = docx.Document(io.BytesIO(data))
    parts: list[str] = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)
