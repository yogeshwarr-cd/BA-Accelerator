from typing import Dict, Any, Optional, List
from backend.validation_export.schemas import ValidationEngineOutput, InvestResult, HallucinationResult
from backend.validation_export.invest_validator import InvestValidator
from backend.validation_export.hallucination_check import HallucinationChecker
from backend.validation_export.coverage_report import CoverageReporter
from backend.shared.logger import get_logger

logger = get_logger(__name__)

async def run(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> ValidationEngineOutput:
    """
    Agent 4: Validation Engine.
    Executes INVEST checks, hallucination checks, coverage checks, and calculates quality rating.
    """
    logger.info("Executing Agent 4 (Validation Engine)...")
    
    stories = input_data.get("user_stories", [])
    requirements = input_data.get("requirements", [])
    
    # 1. Edge case: empty data
    if not stories:
        logger.warning("No stories passed to Agent 4. Approving default empty dataset.")
        return ValidationEngineOutput(
            invest_results=[],
            hallucination_results=[],
            coverage_verified=[],
            quality_score=0.0,
            is_approved=False
        )

    # 2. Trigger concurrent runners
    invest_val = InvestValidator()
    hallucination_chk = HallucinationChecker()
    
    invest_results = await invest_val.validate_all(stories)
    hallucination_results = await hallucination_chk.audit_all(stories, requirements)
    coverage_res = CoverageReporter.calculate_coverage(stories, requirements)

    # 3. Calculate scores
    # 3.1 INVEST score (ratio of True parameters out of total checks)
    total_checks = len(invest_results) * 6
    passed_checks = 0
    for r in invest_results:
        passed_checks += sum([
            1 if r.independent else 0,
            1 if r.negotiable else 0,
            1 if r.valuable else 0,
            1 if r.estimable else 0,
            1 if r.small else 0,
            1 if r.testable else 0
        ])
    invest_score = (passed_checks / total_checks) * 100.0 if total_checks > 0 else 0.0

    # 3.2 Hallucination score (ratio of clean stories)
    hallucination_free = sum([0 if r.has_hallucinations else 1 for r in hallucination_results])
    hallucination_score = (hallucination_free / len(hallucination_results)) * 100.0 if hallucination_results else 0.0

    # 3.3 Coverage score
    coverage_score = coverage_res.get("coverage_percentage", 0.0)

    # 3.4 Aggregated Quality Score (weighted average)
    quality_score = (0.4 * invest_score) + (0.3 * hallucination_score) + (0.3 * coverage_score)
    quality_score = round(quality_score, 2)

    # Approval criteria threshold defaults to 80
    approval_threshold = 80.0
    is_approved = quality_score >= approval_threshold

    logger.info(f"Agent 4 results: Quality={quality_score} (INVEST={invest_score:.1f}%, No-Hallucination={hallucination_score:.1f}%, Coverage={coverage_score:.1f}%), Approved: {is_approved}")

    return ValidationEngineOutput(
        invest_results=invest_results,
        hallucination_results=hallucination_results,
        coverage_verified=coverage_res.get("requirements_covered", []),
        quality_score=quality_score,
        is_approved=is_approved
    )

# INTEGRATION NOTE
# The function implements the signature: async def run(input, config) -> OutputModel.
# The quality score (0-100) dictates if the orchestrator moves to human review or export.
