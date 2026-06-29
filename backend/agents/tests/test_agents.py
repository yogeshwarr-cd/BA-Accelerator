import pytest
from backend.agents.schemas import ExtractedRequirement, RequirementIntelligenceOutput, Agent1RequirementIntelligenceOutput, PrimaryInput, ValidationContext, RetryMetadata, FunctionalRequirement, NonFunctionalRequirement, BusinessRule, Actor, Dependency, Conflict, Ambiguity, MissingRequirement


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


def test_agent1_structured_output_schema():
    """
    Ensures the new Agent 1 payload validates and exposes compatibility properties.
    """
    data = {
        "primary_input": {
            "functional_requirements": [
                {
                    "id": "FR-001",
                    "name": "User Registration",
                    "description": "System shall allow users to register with email",
                    "source_text": "register with email",
                    "traceability_id": "abc123#offset_1",
                }
            ],
            "non_functional_requirements": [
                {
                    "id": "NFR-001",
                    "category": "Performance",
                    "name": "Response Time",
                    "description": "All endpoints must respond within 500ms",
                    "source_text": "respond within 500ms",
                    "traceability_id": "abc123#offset_2",
                }
            ],
            "business_rules": [
                {
                    "id": "BR-001",
                    "type": "Validation Rule",
                    "rule": "Email is mandatory",
                    "description": "Email is required",
                    "source_text": "Email is mandatory",
                    "traceability_id": "abc123#offset_3",
                }
            ],
            "actors": [
                {
                    "id": "ACT-001",
                    "name": "Customer",
                    "type": "Human",
                    "description": "End user",
                }
            ],
            "dependencies": [],
        },
        "validation_context": {
            "conflicts": [],
            "ambiguities": [
                {
                    "requirement": "FR-001",
                    "term": "fast",
                    "issue": "Not quantified",
                }
            ],
            "missing_requirements": [],
            "domain": "Banking & Financial Services",
            "confidence_score": 92,
            "retry_metadata": {
                "attempts": 1,
                "max_attempts": 3,
                "target_confidence": 90,
                "status": "SUCCESS",
                "recommendation": "Ready for Agent-2",
            },
        },
    }

    obj = Agent1RequirementIntelligenceOutput.model_validate(data)
    assert obj.confidence_score == 92.0
    assert len(obj.requirements) == 1
    assert obj.actors == ["Customer"]
    assert obj.business_rules == ["Email is mandatory"]
    assert obj.ambiguities == ["Not quantified"]

# INTEGRATION NOTE
# Verify prompt variables align with these schemas before deploying.
