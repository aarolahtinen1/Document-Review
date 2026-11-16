"""Check how many flagged clauses could be located in the document.

Usage: python scripts/check_quotes.py review.json
Get review.json from:
  curl -s -F file=@samples/services-agreement.docx localhost:8001/review > review.json
"""
import json
import sys

data = json.load(open(sys.argv[1]))
clauses = data["clauses"]
missing = [c for c in clauses if c["location"] is None]
for c in missing:
    print(f"NOT FOUND [{c['severity']}] {c['issue']}: {c['quote'][:100]}")
print(f"{len(clauses) - len(missing)}/{len(clauses)} clauses located in the document")
sys.exit(1 if missing else 0)
