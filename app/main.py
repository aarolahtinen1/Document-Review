"""FastAPI app: review page + /review endpoint."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse

load_dotenv()

from . import extract  # noqa: E402
from .locate import locate  # noqa: E402
from .review import (  # noqa: E402
    EFFORT_OPTIONS,
    MODEL_OPTIONS,
    ReviewError,
    default_settings,
    review_contract,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Contract Review PoC")
INDEX_PATH = Path(__file__).parent / "templates" / "index.html"
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    # Read per request so edits to the page show up on refresh (--reload only watches .py files).
    return INDEX_PATH.read_text(encoding="utf-8")


@app.get("/options")
def options() -> dict:
    """Model/effort choices for the form, with the .env values preselected."""
    model, effort = default_settings()
    return {
        "models": [{"id": k, "label": v} for k, v in MODEL_OPTIONS.items()],
        "efforts": EFFORT_OPTIONS,
        "default_model": model,
        "default_effort": effort,
    }


@app.post("/review")
async def review(
    file: UploadFile | None = File(None),
    model: str = Form(""),
    effort: str = Form(""),
) -> dict:
    default_model, default_effort = default_settings()
    model = model or default_model
    effort = effort or default_effort
    if model not in MODEL_OPTIONS and model != default_model:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    if effort not in EFFORT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown effort level: {effort}")

    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Upload a contract as a PDF or Word document (.pdf or .docx).")
    try:
        doc = extract.from_upload(file.filename, await file.read())
    except extract.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await run_in_threadpool(review_contract, doc, model, effort)
    except ReviewError as e:
        raise HTTPException(status_code=502, detail=str(e))

    clauses = []
    for c in result.clauses:
        loc = locate(c.quote, c.paragraph, doc.paragraphs)
        clauses.append({
            "issue": c.issue,
            "severity": c.severity,
            "quote": c.quote,
            "suggested_edit": c.suggested_edit,
            "location": None if loc is None else {"paragraph": loc.paragraph, "start": loc.start, "end": loc.end},
        })
    # Most severe first, then in document order (unlocated clauses last within their severity).
    clauses.sort(key=lambda c: (
        _SEVERITY_ORDER[c["severity"]],
        c["location"]["paragraph"] if c["location"] else 10**9,
        c["location"]["start"] if c["location"] else 0,
    ))
    for i, c in enumerate(clauses):
        c["id"] = i

    return {
        "source_name": doc.source_name,
        "model": model,
        "effort": effort,
        "paragraphs": doc.paragraphs,
        "clauses": clauses,
    }
