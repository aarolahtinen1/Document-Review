# Document-Review

Proof of concept for automated contract review. Upload a contract as a PDF or Word document (.pdf or .docx). Claude flags the clauses that are problematic for the customer, and the app opens a review screen:

- **Left panel**: one card per flagged clause, showing a severity (high, medium or low), a short issue label, and a redline of the current wording against the **suggested replacement wording**, with a Copy button.
- **Right panel**: the contract, with each flagged clause highlighted. Click a card to jump to its clause, or click a highlight to find its card.

## How it works

```
Browser ──POST /review (.pdf/.docx)─▶ FastAPI ──JSON──▶ review screen
             1. app/extract.py   .docx / .pdf → paragraphs in reading order, numbered [1], [2], … for Claude
             2. app/review.py    Claude + structured outputs → list of flagged clauses
                                 (paragraph number, exact quote, issue, severity, suggested edit)
             3. app/locate.py    finds each quote in the document for highlighting
                                 (whitespace and curly quotes are ignored; unfound quotes are marked as such)
```

| To change…                          | Edit |
|-------------------------------------|------|
| Model or effort (cost vs quality)   | Dropdowns on the upload page; defaults from `CLAUDE_MODEL` / `CLAUDE_EFFORT` in `.env` (restart the server after editing `.env`) |
| What counts as a problem / severity | `app/prompts/system.md` (applies on the next request, no restart) |
| What is returned per clause         | `app/schema.py` (then update `app/main.py` and the page to match) |
| The review screen                   | `app/templates/index.html` |

## Setup (macOS)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env               # then put your key in ANTHROPIC_API_KEY, optionally pick a model
```

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000. If that port is taken, add `--port 8001`. A review usually takes 30–90 seconds.

## API

- `GET /options`: the models and effort levels offered, plus the defaults.
- `POST /review`: a multipart form with `file` (.pdf or .docx) and optional `model` and `effort`. Returns:
  ```json
  {
    "source_name": "contract.docx", "model": "claude-opus-5-5", "effort": "high",
    "paragraphs": ["SERVICES AGREEMENT", "..."],
    "clauses": [{
      "id": 0, "severity": "high", "issue": "Uncapped customer indemnity",
      "quote": "Customer indemnifies Supplier ...", "suggested_edit": "Each party indemnifies ...",
      "location": {"paragraph": 24, "start": 4, "end": 130}
    }]
  }
  ```
  `location` is `null` if the quote couldn't be found in the document.

## Testing and tuning

- `samples/` contains a fictional, deliberately one-sided services agreement as `.docx` (built from the `.txt` with `.venv/bin/python scripts/make_samples.py`) and `.pdf`.
- Save the raw output and check that every quote was found in the document:
  ```bash
  curl -s -F "file=@samples/services-agreement.docx" localhost:8000/review > review.json
  .venv/bin/python scripts/check_quotes.py review.json
  ```

## Notes

- PDF and Word uploads are both converted to plain-text paragraphs before being sent to Claude. That keeps PDFs as cheap as Word documents (Claude would otherwise read every PDF page as text plus an image) and lets highlighting work the same way for both.
- PDF paragraphs are rebuilt from the PDF's text lines using clause numbering, headings and line lengths. This works well for typical contracts, but unusual layouts (multi-column pages, complex tables) may join or split paragraphs oddly. Scanned PDFs with no selectable text are rejected; use a text-based PDF or Word document.
- Contracts are sent to the Anthropic API for processing. Check this is acceptable for the documents you test with.
- The server-side refusal fallback is turned on (`fallbacks="default"` in `app/review.py`) for models that support it (not Haiku). If Claude declines a request, the API retries it on a suitable fallback model.
- The output is a first-pass aid, not legal advice.
