# Document-Review

Proof of concept for automated contract review. Upload a contract (PDF, DOCX or pasted text). Claude reviews it against the system prompt and you get back a structured PDF report covering:

- **Key terms**: parties, dates, term and renewal, governing law, payment, value, termination, liability cap
- **Risk flags**: rated high, medium or low, each with an explanation and a suggested action
- **Obligations** and **key dates**
- **Missing or unusual** provisions

Every finding includes the verbatim clause it came from, so a reviewer can check it.

## How it works

```
Browser ──POST /review──▶ FastAPI
                           1. app/extract.py   PDF → sent as-is · DOCX → text · pasted text
                           2. app/review.py    Claude (claude-opus-5-5) + structured outputs → ContractReview JSON
                           3. app/report.py    Jinja2 HTML template → WeasyPrint → PDF
```

| To change…                         | Edit                          |
|------------------------------------|-------------------------------|
| Model or effort (cost vs quality)  | `CLAUDE_MODEL` / `CLAUDE_EFFORT` in `.env` (restart the server after changing) |
| How the review behaves / risk rules | `app/prompts/system.md` (applies on the next request, no restart) |
| Which labels are extracted          | `app/schema.py` (then update the template to match) |
| How the PDF looks                   | `app/templates/report.html`   |

## Setup (macOS)

```bash
brew install pango                 # WeasyPrint's PDF rendering dependency
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env               # then put your key in ANTHROPIC_API_KEY, optionally pick a model
```

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000. A review usually takes 30–90 seconds.

## Testing and tuning

- `samples/` contains a fictional, deliberately one-sided services agreement in .txt, .docx and .pdf form. Rebuild the .docx and .pdf versions with `.venv/bin/python scripts/make_samples.py`.
- Get the raw structured output instead of a PDF:
  ```bash
  curl -s -F "text=<samples/services-agreement.txt" "localhost:8000/review?format=json" > review.json
  ```
- Check that every quote really appears in the source:
  ```bash
  .venv/bin/python scripts/check_quotes.py review.json samples/services-agreement.txt
  ```

## Notes

- Contracts are sent to the Anthropic API for processing. Check this is acceptable for the documents you test with.
- The server-side refusal fallback is turned on (`fallbacks="default"` in `app/review.py`) for models that support it (not Haiku). If Claude declines a request, the API retries it on a suitable fallback model.
- The output is a first-pass aid, not legal advice.
