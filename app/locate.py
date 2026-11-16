"""Find where each quoted clause sits in the document, for highlighting."""

import re
from dataclasses import dataclass

# Characters treated as equivalent when matching (curly quotes, dashes, odd spaces).
_CHAR_MAP = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ",
})


@dataclass
class Location:
    paragraph: int  # 0-based index into the paragraphs list
    start: int      # character offsets into that paragraph's original text
    end: int


def _normalise(text: str) -> tuple[str, list[int]]:
    """Lower-case, unify punctuation, collapse whitespace.

    Returns the normalised string and, for each of its characters, the index of
    the original character it came from (so matches map back to real offsets).
    """
    out: list[str] = []
    index: list[int] = []
    prev_space = True  # also strips leading whitespace
    for i, ch in enumerate(text.translate(_CHAR_MAP)):
        if ch.isspace():
            if prev_space:
                continue
            out.append(" ")
            index.append(i)
            prev_space = True
        else:
            out.append(ch.lower())
            index.append(i)
            prev_space = False
    if out and out[-1] == " ":
        out.pop()
        index.pop()
    return "".join(out), index


def _find_in(paragraph: str, quote_norm: str) -> tuple[int, int] | None:
    para_norm, index = _normalise(paragraph)
    pos = para_norm.find(quote_norm)
    if pos < 0:
        return None
    return index[pos], index[pos + len(quote_norm) - 1] + 1


def locate(quote: str, paragraph_number: int, paragraphs: list[str]) -> Location | None:
    """Locate `quote`, trying the paragraph Claude named first, then the rest."""
    quote_norm, _ = _normalise(quote.strip().strip('"').strip("'"))
    quote_norm = re.sub(r"(\.\.\.|…)$", "", quote_norm).strip()
    if not quote_norm:
        return None

    stated = paragraph_number - 1
    order = ([stated] if 0 <= stated < len(paragraphs) else []) + [
        i for i in range(len(paragraphs)) if i != stated
    ]
    for i in order:
        span = _find_in(paragraphs[i], quote_norm)
        if span:
            return Location(paragraph=i, start=span[0], end=span[1])
    return None
