from typing import Dict, Any, Optional
from backend.agents.schemas import EpicFeaturePlannerOutput
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

async def run(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> EpicFeaturePlannerOutput:
    """
    Agent 2: Epic & Feature Planner.
    Groups requirements into modular Epics, Features, and logs mapping traceability hierarchy.
    """
    logger.info("Executing Agent 2 (Epic & Feature Planner)...")
    
    requirements = input_data.get("requirements", [])
    if not requirements:
        logger.warning("Empty requirements list passed to Agent 2. Returning empty plan.")
        return EpicFeaturePlannerOutput(epics=[], features=[], hierarchy=[])

    # Convert Pydantic objects to list of dicts if needed
    serializable_requirements = []
    for req in requirements:
        if hasattr(req, "model_dump"):
            serializable_requirements.append(req.model_dump())
        else:
            serializable_requirements.append(req)

    # 1. Render template prompt
    renderer = JinjaRenderer()
    prompt = renderer.render("agent2.jinja2", {"requirements": serializable_requirements})
    
    system_prompt = "You are a lead Agile Product Architect. Structure requirements into clean Epics and Features. Output raw JSON."

    # 2. Invoke LLM client
    llm = LLMClient()
    response_json = await llm.generate_json(prompt=prompt, system_prompt=system_prompt)
    
    # 3. Cast to Pydantic structure
    output = EpicFeaturePlannerOutput.model_validate(response_json)
    logger.info(f"Agent 2 run completed. Structured {len(output.epics)} epics and {len(output.features)} features.")
    
    return output

# INTEGRATION NOTE
# Epic Feature Planner output aligns requirements with feature boundaries.
# Maintain target signatures so M3 Orchestrator state updates function smoothly.
