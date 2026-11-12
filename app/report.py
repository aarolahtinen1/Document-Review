"""Render a ContractReview to a PDF."""

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from .schema import ContractReview

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

KEY_TERM_LABELS = {
    "effective_date": "Effective date",
    "term_and_renewal": "Term & renewal",
    "governing_law": "Governing law",
    "payment_terms": "Payment terms",
    "contract_value": "Contract value",
    "termination_rights": "Termination rights",
    "liability_cap": "Liability cap",
}


def render_html(review: ContractReview, source_name: str, settings: str = "") -> str:
    risks = sorted(review.risk_flags, key=lambda r: _SEVERITY_ORDER[r.severity])
    counts = {s: sum(r.severity == s for r in risks) for s in _SEVERITY_ORDER}
    key_terms = [(label, getattr(review.key_terms, field)) for field, label in KEY_TERM_LABELS.items()]
    return _env.get_template("report.html").render(
        review=review,
        risks=risks,
        counts=counts,
        key_terms=key_terms,
        source_name=source_name,
        settings=settings,
        review_date=date.today().strftime("%d %B %Y"),
    )


def render_pdf(review: ContractReview, source_name: str, settings: str = "") -> bytes:
    return HTML(string=render_html(review, source_name, settings)).write_pdf()
