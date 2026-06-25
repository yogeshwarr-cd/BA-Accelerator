import pytest
from backend.validation_export.coverage_report import CoverageReporter

def test_coverage_calculation():
    """
    Validates trace ratio computation when requirements map to stories.
    """
    requirements = [
        {"id": "REQ-001", "content": "Login module"},
        {"id": "REQ-002", "content": "Signup module"}
    ]
    stories = [
        {"id": "STORY-1", "trace_mappings": ["REQ-001"]}
    ]
    
    report = CoverageReporter.calculate_coverage(stories, requirements)
    assert report["coverage_percentage"] == 50.0
    assert "REQ-001" in report["requirements_covered"]
    assert "REQ-002" in report["requirements_uncovered"]

# INTEGRATION NOTE
# The coverage reporter requires matching IDs. Check trace_mappings format.
