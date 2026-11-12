"""FastAPI app: upload form + /review endpoint."""

import logging
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, Response

load_dotenv()

from . import extract, report  # noqa: E402
from .review import (  # noqa: E402
    EFFORT_OPTIONS,
    MODEL_OPTIONS,
    ReviewError,
    default_settings,
    review_contract,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)

app = FastAPI(title="Contract Review PoC")
INDEX_PATH = Path(__file__).parent / "templates" / "index.html"


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
    text: str = Form(""),
    model: str = Form(""),
    effort: str = Form(""),
    format: str = "pdf",
):
    default_model, default_effort = default_settings()
    model = model or default_model
    effort = effort or default_effort
    if model not in MODEL_OPTIONS and model != default_model:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    if effort not in EFFORT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown effort level: {effort}")

    try:
        if file is not None and file.filename:
            doc = extract.from_upload(file.filename, await file.read())
        else:
            doc = extract.from_text(text)
    except extract.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await run_in_threadpool(review_contract, doc, model, effort)
    except ReviewError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if format == "json":
        return JSONResponse(result.model_dump())

    settings = f"{model}, effort {effort}"
    pdf = await run_in_threadpool(report.render_pdf, result, doc.source_name, settings)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(doc.source_name).stem).strip("-") or "contract"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{stem}-review.pdf"'},
    )
