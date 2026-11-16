"""The label schema: what the review returns for each contract.

Claude's output is constrained to this shape (structured outputs).
"""

from typing import Literal

from pydantic import BaseModel, Field


class FlaggedClause(BaseModel):
    paragraph: int = Field(description="The [n] number of the paragraph the quote is taken from.")
    quote: str = Field(description="The problematic text, copied exactly from that one paragraph.")
    issue: str = Field(description="Short label for the problem, e.g. 'Uncapped customer indemnity'.")
    severity: Literal["high", "medium", "low"]
    suggested_edit: str = Field(
        description="Replacement wording for the quoted text, ready to paste into the contract in place of the quote."
    )


class ContractReview(BaseModel):
    clauses: list[FlaggedClause]
