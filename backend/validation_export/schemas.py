from pydantic import BaseModel, Field
from typing import List, Optional

class InvestResult(BaseModel):
    story_id: str = Field(..., description="ID of the checked user story")
    independent: bool = Field(default=True, description="Does the story avoid dependencies on other stories?")
    negotiable: bool = Field(default=True, description="Is there room for discussion/negotiation in scope?")
    valuable: bool = Field(default=True, description="Does it provide clear value to actors/end users?")
    estimable: bool = Field(default=True, description="Is the work sizing clear enough for development estimating?")
    small: bool = Field(default=True, description="Is the story appropriately sized to fit in a single iteration?")
    testable: bool = Field(default=True, description="Does it contain Gherkin scenarios to permit clear test confirmation?")
    feedback: str = Field(default="", description="Constructive critiques on fails")

class HallucinationResult(BaseModel):
    story_id: str = Field(..., description="ID of the checked user story")
    has_hallucinations: bool = Field(..., description="True if story contains features unsupported by source requirements")
    unsupported_elements: List[str] = Field(default_factory=list, description="Text segments or requirements created without source mapping")
    feedback: str = Field(default="", description="Auditor explanation of inconsistencies")

class ValidationEngineOutput(BaseModel):
    invest_results: List[InvestResult] = Field(..., description="INVEST guidelines scorecard metrics")
    hallucination_results: List[HallucinationResult] = Field(..., description="Audit of story details to requirements alignment")
    coverage_verified: List[str] = Field(..., description="List of source requirement IDs trace mapped in stories")
    quality_score: float = Field(..., description="Aggregated metric score representing story set readiness (0-100)")
    is_approved: bool = Field(..., description="Flag identifying if validation meets approval thresholds (e.g. >= 80)")

# INTEGRATION NOTE
# Member 5 (validation) exports this schema model which Agent 4 populates.
# Changes to quality scoring thresholds are managed inside agent4_validation_engine.py.
