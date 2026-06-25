from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestrator.state import GraphState
from backend.orchestrator.router import route_after_agent1, route_after_validation
from backend.orchestrator.retry_handler import RetryHandler

# Import agent modules (Member 2 & Member 5)
from backend.agents import agent1_requirement_intelligence
from backend.agents import agent2_epic_feature_planner
from backend.agents import agent3_user_story_generator
from backend.validation_export import agent4_validation_engine

# Import database session & log model (Member 4)
from backend.db.postgres import AsyncSessionLocal
from backend.db.models import AuditLog, Story, Requirement, Job
from backend.shared.logger import get_logger

logger = get_logger(__name__)

# --- Helper function for audit logging ---
async def write_audit_log(job_id: str, node_name: str, status: str, message: str, payload: Dict[str, Any] = None) -> None:
    async with AsyncSessionLocal() as session:
        try:
            log = AuditLog(
                job_id=job_id,
                node_name=node_name,
                status=status,
                message=message,
                payload=payload or {}
            )
            session.add(log)
            await session.commit()
        except Exception as e:
            logger.error(f"Audit log writing failed: {str(e)}")

# --- Node Implementations ---

async def ingest_node(state: GraphState) -> Dict[str, Any]:
    """
    Initial node to prepare the graph execution context.
    Logs start execution to the audit database.
    """
    job_id = state["job_id"]
    logger.info(f"Pipeline started for job: {job_id}")
    await write_audit_log(job_id, "ingest", "COMPLETED", "Document ingestion setup complete.", {
        "source_type": state.get("source_type"),
        "fingerprint": state.get("fingerprint")
    })
    return {"status": "RUNNING"}

async def agent1_node(state: GraphState) -> Dict[str, Any]:
    """
    Node for Agent 1. Extracts requirements and confidence.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "agent1", "STARTED", "Agent 1 Requirement Extraction initiated.")
    
    input_data = {"raw_text": state["raw_text"]}
    # Run Agent 1
    result = await agent1_requirement_intelligence.run(input_data)
    
    # Store requirements in DB
    async with AsyncSessionLocal() as session:
        # Clear existing requirements for this job to avoid duplicate entries in retries
        from sqlalchemy import delete
        await session.execute(delete(Requirement).where(Requirement.job_id == job_id))
        
        db_reqs = []
        for req in result.requirements:
            db_reqs.append(Requirement(
                job_id=job_id,
                content=req.content,
                actors=req.actors,
                business_rules=req.business_rules,
                trace_id=req.id,
                confidence_score=result.confidence_score
            ))
        session.add_all(db_reqs)
        await session.commit()

    await write_audit_log(job_id, "agent1", "COMPLETED", f"Extracted {len(result.requirements)} requirements.", {
        "confidence_score": result.confidence_score,
        "requirements_count": len(result.requirements)
    })

    return {
        "requirements": [req.model_dump() for req in result.requirements],
        "actors": result.actors,
        "business_rules": result.business_rules,
        "ambiguities": result.ambiguities,
        "conflicts": result.conflicts,
        "confidence_score": result.confidence_score
    }

async def retry_node(state: GraphState) -> Dict[str, Any]:
    """
    Increments retry values for low-confidence results.
    """
    job_id = state["job_id"]
    updated_state = RetryHandler.inspect_and_increment(dict(state))
    
    await write_audit_log(
        job_id, 
        "retry_handler", 
        "RETRY", 
        f"Low confidence (score: {state.get('confidence_score')}). Retrying... Attempt {updated_state['retry_count']}"
    )
    
    return {
        "retry_count": updated_state["retry_count"],
        "status": updated_state["status"]
    }

async def agent2_node(state: GraphState) -> Dict[str, Any]:
    """
    Node for Agent 2. Plans Epics and Features.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "agent2", "STARTED", "Agent 2 Epic & Feature Planning initiated.")
    
    input_data = {"requirements": state["requirements"]}
    result = await agent2_epic_feature_planner.run(input_data)
    
    await write_audit_log(job_id, "agent2", "COMPLETED", "Structured epics and features.", {
        "epics_count": len(result.epics),
        "features_count": len(result.features)
    })
    
    return {
        "epics": [epic.model_dump() for epic in result.epics],
        "features": [feat.model_dump() for feat in result.features],
        "hierarchy": [h.model_dump() for h in result.hierarchy]
    }

async def agent3_node(state: GraphState) -> Dict[str, Any]:
    """
    Node for Agent 3. Generates Agile User Stories.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "agent3", "STARTED", "Agent 3 User Story Generation initiated.")
    
    input_data = {
        "epics": state["epics"],
        "features": state["features"],
        "hierarchy": state["hierarchy"],
        "requirements": state["requirements"]
    }
    result = await agent3_user_story_generator.run(input_data)
    
    # Store stories in DB
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        await session.execute(delete(Story).where(Story.job_id == job_id))
        
        db_stories = []
        for story in result.user_stories:
            db_stories.append(Story(
                job_id=job_id,
                epic=story.epic_id,
                feature=story.feature_id,
                title=story.title,
                user_story=story.user_story_text,
                acceptance_criteria=[ac.model_dump() for ac in story.acceptance_criteria],
                trace_mappings=story.trace_mappings,
                plain_text_summary=result.plain_text_summary
            ))
        session.add_all(db_stories)
        await session.commit()

    await write_audit_log(job_id, "agent3", "COMPLETED", f"Generated {len(result.user_stories)} user stories.")
    
    return {
        "user_stories": [s.model_dump() for s in result.user_stories],
        "plain_text_summary": result.plain_text_summary
    }

async def agent4_node(state: GraphState) -> Dict[str, Any]:
    """
    Node for Agent 4. Validates stories against criteria (INVEST/Hallucination/Coverage).
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "agent4", "STARTED", "Agent 4 Validation Engine initiated.")
    
    input_data = {
        "user_stories": state["user_stories"],
        "requirements": state["requirements"]
    }
    result = await agent4_validation_engine.run(input_data)
    
    # Save validation results back to Stories in DB
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        stmt = select(Story).where(Story.job_id == job_id)
        db_stories_res = await session.execute(stmt)
        db_stories = db_stories_res.scalars().all()
        
        # Match generated stories and set results
        story_val_map = {v.story_id: v.model_dump() for v in result.invest_results}
        for dbs in db_stories:
            # Match title or custom ID mapping
            # For simplicity, match based on order or trace mapping
            val = story_val_map.get(dbs.id) or {}
            dbs.validation_results = {
                "invest_checks": val,
                "coverage_verified": dbs.trace_mappings[0] in result.coverage_verified if dbs.trace_mappings else False
            }
        await session.commit()

    await write_audit_log(job_id, "agent4", "COMPLETED", f"Validation run completed. Quality Score: {result.quality_score}/100.", {
        "quality_score": result.quality_score,
        "is_approved": result.is_approved
    })

    return {
        "validation_results": result.model_dump(),
        "quality_score": result.quality_score,
        "is_approved": result.is_approved
    }

async def human_review_node(state: GraphState) -> Dict[str, Any]:
    """
    Placeholder review node. Execution pauses here until human intervention.
    """
    job_id = state["job_id"]
    logger.info(f"Pipeline paused for job {job_id}. Awaiting manual approval.")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        stmt = update(Job).where(Job.id == job_id).values(status="HUMAN_REVIEW")
        await session.execute(stmt)
        await session.commit()

    await write_audit_log(job_id, "human_review", "COMPLETED", "Pipeline execution paused. Awaiting human input.")
    return {"status": "HUMAN_REVIEW"}

async def export_node(state: GraphState) -> Dict[str, Any]:
    """
    Executes default structured JSON file export.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "export", "STARTED", "Export execution started.")
    
    # Save state outcome to job table
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        stmt = update(Job).where(Job.id == job_id).values(status="COMPLETED")
        await session.execute(stmt)
        await session.commit()

    await write_audit_log(job_id, "export", "COMPLETED", "User stories exported successfully to DB. Execution finished.")
    return {"status": "COMPLETED"}

async def fail_node(state: GraphState) -> Dict[str, Any]:
    """
    Fail safe terminal state.
    """
    job_id = state["job_id"]
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        stmt = update(Job).where(Job.id == job_id).values(status="FAILED", error_message="Confidence threshold failure.")
        await session.execute(stmt)
        await session.commit()

    await write_audit_log(job_id, "pipeline", "FAILED", "Workflow aborted due to low confidence rating.")
    return {"status": "FAILED"}

# --- Graph Compilation ---

workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("ingest", ingest_node)
workflow.add_node("agent1", agent1_node)
workflow.add_node("retry", retry_node)
workflow.add_node("agent2", agent2_node)
workflow.add_node("agent3", agent3_node)
workflow.add_node("agent4", agent4_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("export", export_node)
workflow.add_node("fail", fail_node)

# Configure Edges
workflow.set_entry_point("ingest")
workflow.add_edge("ingest", "agent1")

# Route after Agent 1
workflow.add_conditional_edges(
    "agent1",
    route_after_agent1,
    {
        "retry_node": "retry",
        "agent2_node": "agent2",
        "fail_node": "fail"
    }
)
workflow.add_edge("retry", "agent1")

workflow.add_edge("agent2", "agent3")
workflow.add_edge("agent3", "agent4")

# Route after Validation
workflow.add_conditional_edges(
    "agent4",
    route_after_validation,
    {
        "export_node": "export",
        "human_review_node": "human_review"
    }
)

# Human review completion edge
workflow.add_edge("human_review", "export")
workflow.add_edge("export", END)
workflow.add_edge("fail", END)

# Memory saver for tracking checkpoint thread state
memory_store = MemorySaver()

# Compile the graph. Interrupt execution before entering human_review node.
pipeline_graph = workflow.compile(
    checkpointer=memory_store,
    interrupt_before=["human_review"]
)

# INTEGRATION NOTE
# StateGraph uses MemorySaver to serialize process context threads.
# Call `pipeline_graph.ainvoke` with a unique thread configuration dictionary to enable bookmarks.
