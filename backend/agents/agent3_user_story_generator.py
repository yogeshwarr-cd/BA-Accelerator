from typing import Dict, Any, Optional
from backend.agents.schemas import UserStoryGeneratorOutput
from backend.shared.jinja_renderer import JinjaRenderer
from backend.shared.llm_client import LLMClient
from backend.shared.logger import get_logger

logger = get_logger(__name__)

async def run(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> UserStoryGeneratorOutput:
    """
    Agent 3: User Story Generator.
    Generates Agile stories with Given-When-Then acceptance tests based on planners' outputs.
    """
    logger.info("Executing Agent 3 (User Story Generator)...")
    
    epics = input_data.get("epics", [])
    features = input_data.get("features", [])
    hierarchy = input_data.get("hierarchy", [])
    requirements = input_data.get("requirements", [])

    if not features:
        logger.warning("Empty features list passed to Agent 3. Returning empty stories.")
        return UserStoryGeneratorOutput(user_stories=[], plain_text_summary="No features found. Story generation skipped.")

    # Helper function to serialize any Pydantic model in inputs
    def serialize_list(items):
        res = []
        for item in items:
            if hasattr(item, "model_dump"):
                res.append(item.model_dump())
            else:
                res.append(item)
        return res

    # 1. Render template prompt
    renderer = JinjaRenderer()
    prompt = renderer.render(
        "agent3.jinja2", 
        {
            "epics": serialize_list(epics),
            "features": serialize_list(features),
            "hierarchy": serialize_list(hierarchy),
            "requirements": serialize_list(requirements)
        }
    )
    
    system_prompt = "You are a professional Product Owner. Draft functional User Stories with detailed Gherkin Acceptance Criteria. Output raw JSON."

    # 2. Invoke LLM client
    llm = LLMClient()
    response_json = await llm.generate_json(prompt=prompt, system_prompt=system_prompt)
    
    # 3. Cast to Pydantic structure
    output = UserStoryGeneratorOutput.model_validate(response_json)
    logger.info(f"Agent 3 run completed. Generated {len(output.user_stories)} user stories.")
    
    return output

# INTEGRATION NOTE
# User Story output links back to EPIC and FEATURE IDs for compliance.
# Prompts are loaded from agent3.jinja2. Check variables inside that template if modifying schemas.
