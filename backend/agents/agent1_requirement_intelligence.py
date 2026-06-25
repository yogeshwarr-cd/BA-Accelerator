from typing import Dict, Any, Optional
from backend.agents.schemas import RequirementIntelligenceOutput
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

async def run(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> RequirementIntelligenceOutput:
    """
    Agent 1: Requirement Intelligence.
    Extracts requirements, actors, rules, ambiguities, conflicts, and confidence score.
    """
    logger.info("Executing Agent 1 (Requirement Intelligence)...")
    
    raw_text = input_data.get("raw_text", "")
    if not raw_text:
        logger.warning("Empty raw_text passed to Agent 1. Returning empty outputs.")
        return RequirementIntelligenceOutput(
            requirements=[],
            actors=[],
            business_rules=[],
            ambiguities=["No content was provided for analysis."],
            conflicts=[],
            confidence_score=0.0
        )

    # 1. Render template prompt
    renderer = JinjaRenderer()
    prompt = renderer.render("agent1.jinja2", {"raw_text": raw_text})
    
    system_prompt = "You are a senior Business Analyst. Analyze the document precisely. Output raw, clean JSON."

    # 2. Invoke LLM client
    llm = LLMClient()
    response_json = await llm.generate_json(prompt=prompt, system_prompt=system_prompt)
    
    # 3. Cast to Pydantic structure
    output = RequirementIntelligenceOutput.model_validate(response_json)
    logger.info(f"Agent 1 run completed. Extracted {len(output.requirements)} requirements. Confidence: {output.confidence_score}")
    
    return output

# INTEGRATION NOTE
# This module implements the signature async def run(input, config) -> OutputModel.
# Do not modify the function parameters as it is integrated directly into the Orchestrator.
