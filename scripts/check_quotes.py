"""Check that every quote in a review JSON appears verbatim in the source text.

Usage: python scripts/check_quotes.py review.json source.txt
Get review.json from: curl -F file=@samples/services-agreement.txt "localhost:8000/review?format=json"
"""
import json
import re
import sys


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def quotes(review: dict):
    kt = review["key_terms"]
    for p in kt["parties"]:
        yield "party", p["quote"]
    for k, v in kt.items():
        if k != "parties" and v:
            yield k, v["quote"]
    for section in ("risk_flags", "obligations", "key_dates"):
        for item in review[section]:
            yield section, item["quote"]


review = json.load(open(sys.argv[1]))
source = norm(open(sys.argv[2]).read())
total = bad = 0
for where, q in quotes(review):
    total += 1
    if norm(q) not in source:
        bad += 1
        print(f"NOT VERBATIM [{where}]: {q[:100]}")
print(f"{total - bad}/{total} quotes found verbatim")
sys.exit(1 if bad else 0)
