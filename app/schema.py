"""The label schema: what the review extracts from each contract.

Claude's output is constrained to this shape (structured outputs), so changing
a field here changes what the model returns and what the PDF can show.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    value: str = Field(description="Plain-English statement of the term.")
    quote: str = Field(description="Verbatim text copied from the contract that supports the value.")
    section_ref: Optional[str] = Field(description="Clause/section number or heading, if identifiable.")


class KeyTerms(BaseModel):
    parties: list[Finding] = Field(description="Each contracting party, with its role (e.g. supplier, customer).")
    effective_date: Optional[Finding]
    term_and_renewal: Optional[Finding]
    governing_law: Optional[Finding]
    payment_terms: Optional[Finding]
    contract_value: Optional[Finding]
    termination_rights: Optional[Finding]
    liability_cap: Optional[Finding]


class RiskFlag(BaseModel):
    title: str = Field(description="Short label for the risk, e.g. 'Uncapped indemnity'.")
    severity: Literal["high", "medium", "low"]
    explanation: str = Field(description="Why this clause is a risk, from the reviewing party's perspective.")
    quote: str = Field(description="Verbatim text of the clause.")
    section_ref: Optional[str]
    suggested_action: str = Field(description="What a reviewer might negotiate or check.")


class Obligation(BaseModel):
    party: str
    description: str
    due: Optional[str] = Field(description="Deadline, frequency or trigger, if any.")
    quote: str
    section_ref: Optional[str]


class KeyDate(BaseModel):
    label: str = Field(description="What the date is, e.g. 'Renewal notice deadline'.")
    date: str = Field(description="The date or how it is calculated, as stated in the contract.")
    quote: str
    section_ref: Optional[str]


class ContractReview(BaseModel):
    document_type: str = Field(description="e.g. 'Mutual NDA', 'Master Services Agreement'.")
    summary: str = Field(description="One paragraph describing what the contract does.")
    key_terms: KeyTerms
    risk_flags: list[RiskFlag]
    obligations: list[Obligation]
    key_dates: list[KeyDate]
    missing_or_unusual: list[str] = Field(
        description="Standard protections that are absent, or provisions that are unusual for this contract type."
    )
