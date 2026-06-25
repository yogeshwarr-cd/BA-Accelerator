import pytest
from backend.agents.schemas import ExtractedRequirement, RequirementIntelligenceOutput

def test_pydantic_extraction_schemas():
    """
    Verifies that requirement schemas enforce types correctly.
    """
    req = ExtractedRequirement(
        id="REQ-001",
        content="System must allow email verification",
        actors=["Customer"],
        business_rules=["Token expires in 24 hours"]
    )
    assert req.id == "REQ-001"
    assert "Customer" in req.actors

def test_requirement_output_schema():
    """
    Ensures requirement agent payload output structure validates successfully.
    """
    data = {
        "requirements": [
            {"id": "REQ-001", "content": "Auth user", "actors": ["Admin"], "business_rules": []}
        ],
        "actors": ["Admin"],
        "business_rules": [],
        "ambiguities": [],
        "conflicts": [],
        "confidence_score": 0.95
    }
    obj = RequirementIntelligenceOutput.model_validate(data)
    assert obj.confidence_score == 0.95
    assert len(obj.requirements) == 1

# INTEGRATION NOTE
# Verify prompt variables align with these schemas before deploying.
