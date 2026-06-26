from typing import Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestrator.state import GraphState
from backend.orchestrator.router import route_after_agent1, route_after_validation
from backend.orchestrator.retry_handler import RetryHandler

# Import agent modules
from backend.agents import agent1_requirement_intelligence
from backend.agents import agent2_epic_feature_planner
from backend.agents import agent3_user_story_generator
from backend.validation_export import agent4_validation_engine

# Import database session & log model
from backend.db.postgres import AsyncSessionLocal
from backend.db.models import AuditLog, Story, Requirement, Job
from backend.shared.logger import get_logger

logger = get_logger(__name__)

# --- Helper Functions for Orchestration ---

def _merge_outputs(state: GraphState) -> Dict[str, Any]:
    """
    Merge Agent-1 and Agent-2 outputs into a unified context.
    """
    return {
        "master_context": {
            "job_id": state.get("job_id"),
            "requirements": state.get("requirements", []),
            "actors": state.get("actors", []),
            "business_rules": state.get("business_rules", []),
            "validation_context": {
                "ambiguities": state.get("ambiguities", []),
                "conflicts": state.get("conflicts", [])
            },
            "epics": state.get("epics", []),
            "features": state.get("features", []),
            "hierarchy": state.get("epic_hierarchy", state.get("hierarchy", [])),
            "priority": state.get("priority", []),
            "coverage_report": state.get("coverage_report", {}),
            "dependencies": state.get("dependencies", []),
            "metadata": state.get("metadata", {}),
            "traceability_matrix": state.get("traceability_matrix", []),
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    }

def _build_story_contexts(master_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build individual story contexts from the traceability matrix.
    One story context per mapped requirement.
    """
    story_contexts = []
    traceability_matrix = master_context.get("traceability_matrix", [])
    
    # Create lookup maps for quick access
    epics_map = {epic.get("id"): epic for epic in master_context.get("epics", [])}
    features_map = {feat.get("id"): feat for feat in master_context.get("features", [])}
    priority_map = {p.get("feature_id"): p.get("priority", "Medium") for p in master_context.get("priority", [])}
    requirements_map = {req.get("id"): req for req in master_context.get("requirements", [])}
    dependencies_map = {}
    
    # Build dependency map by feature_id
    for dep in master_context.get("dependencies", []):
        dep_feat_id = dep.get("dependent_feature_id")
        if dep_feat_id not in dependencies_map:
            dependencies_map[dep_feat_id] = []
        dependencies_map[dep_feat_id].append(dep.get("dependency_feature_id"))
    
    # Create story context for each requirement in traceability matrix
    for trace_entry in traceability_matrix:
        req_id = trace_entry.get("requirement_id")
        epic_id = trace_entry.get("epic_id")
        feature_id = trace_entry.get("feature_id")
        
        requirement = requirements_map.get(req_id, {})
        epic = epics_map.get(epic_id, {})
        feature = features_map.get(feature_id, {})
        
        story_context = {
            "story_id": f"STORY-{req_id}",
            "requirement_id": req_id,
            "requirement": requirement.get("content", ""),
            "epic": {
                "id": epic.get("id", ""),
                "name": epic.get("name", ""),
                "description": epic.get("description", "")
            },
            "feature": {
                "id": feature.get("id", ""),
                "name": feature.get("name", ""),
                "description": feature.get("description", ""),
                "priority": priority_map.get(feature_id, "Medium")
            },
            "actor": requirement.get("actors")[0] if requirement.get("actors") else "",
            "business_rules": requirement.get("business_rules", []),
            "dependencies": dependencies_map.get(feature_id, []),
            "priority": priority_map.get(feature_id, "Medium"),
            "validation": {
                "ambiguities": [],
                "conflicts": []
            },
            "traceability": {
                "requirement_id": req_id,
                "epic_id": epic_id,
                "feature_id": feature_id,
                "dependencies": trace_entry.get("dependencies", [])
            }
        }
        
        story_contexts.append(story_context)
    
    return story_contexts

# --- Audit Logging Helper ---
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

async def confidence_check_node(state: GraphState) -> Dict[str, Any]:
    """
    Confidence check after Agent 1. Determines if retry is needed.
    """
    job_id = state["job_id"]
    confidence_score = state.get("confidence_score", 0.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    logger.info(f"Confidence check: score={confidence_score}, retry_count={retry_count}, max_retries={max_retries}")
    
    if confidence_score < 0.75 and retry_count < max_retries:
        await write_audit_log(
            job_id,
            "confidence_check",
            "RETRY",
            f"Low confidence ({confidence_score:.2f}). Retrying... Attempt {retry_count + 1}/{max_retries}"
        )
        return {
            "retry_count": retry_count + 1,
            "status": "RETRYING"
        }
    
    await write_audit_log(
        job_id,
        "confidence_check",
        "PASSED" if confidence_score >= 0.75 else "FAILED",
        f"Confidence check completed. Score: {confidence_score:.2f}"
    )
    
    return {"status": "CONFIDENCE_OK"}

async def agent2_node(state: GraphState) -> Dict[str, Any]:
    """
    Node for Agent 2. Plans Epics and Features with comprehensive outputs.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "agent2", "STARTED", "Agent 2 Epic & Feature Planning initiated.")
    
    input_data = {"requirements": state["requirements"]}
    result = await agent2_epic_feature_planner.run(input_data)
    
    await write_audit_log(job_id, "agent2", "COMPLETED", "Structured epics, features, and dependencies.", {
        "epics_count": len(result.epics),
        "features_count": len(result.features),
        "coverage_percentage": result.coverage_report.coverage_percentage,
        "confidence_score": result.metadata.confidence_score
    })
    
    return {
        "epics": [epic.model_dump() for epic in result.epics],
        "features": [feat.model_dump() for feat in result.features],
        "hierarchy": [h.model_dump() for h in result.hierarchy],
        "requirement_mapping": [rm.model_dump() for rm in result.requirement_mapping],
        "epic_hierarchy": [eh.model_dump() for eh in result.epic_hierarchy],
        "dependencies": [d.model_dump() for d in result.dependencies],
        "priority": [p.model_dump() for p in result.priority],
        "coverage_report": result.coverage_report.model_dump(),
        "metadata": result.metadata.model_dump(),
        "traceability_matrix": [tm.model_dump() for tm in result.traceability_matrix]
    }

async def merge_outputs_node(state: GraphState) -> Dict[str, Any]:
    """
    Non-LLM orchestrator node. Merges Agent-1 and Agent-2 outputs.
    """
    job_id = state["job_id"]
    logger.info(f"Merging Agent-1 and Agent-2 outputs for job {job_id}")
    
    await write_audit_log(job_id, "merge_outputs", "STARTED", "Merging Agent-1 and Agent-2 outputs into MasterContext.")
    
    merge_result = _merge_outputs(state)
    
    await write_audit_log(job_id, "merge_outputs", "COMPLETED", "MasterContext created successfully.", {
        "epics_count": len(merge_result["master_context"].get("epics", [])),
        "features_count": len(merge_result["master_context"].get("features", [])),
        "requirements_count": len(merge_result["master_context"].get("requirements", []))
    })
    
    return merge_result

async def build_story_contexts_node(state: GraphState) -> Dict[str, Any]:
    """
    Non-LLM orchestrator node. Builds individual story contexts from traceability matrix.
    Generates one story context per mapped requirement.
    """
    job_id = state["job_id"]
    master_context = state.get("master_context", {})
    
    logger.info(f"Building story contexts from traceability matrix for job {job_id}")
    
    await write_audit_log(job_id, "build_story_contexts", "STARTED", "Building individual story contexts from traceability matrix.")
    
    story_contexts = _build_story_contexts(master_context)
    
    await write_audit_log(job_id, "build_story_contexts", "COMPLETED", f"Built {len(story_contexts)} story contexts.", {
        "story_contexts_count": len(story_contexts)
    })
    
    return {"story_contexts": story_contexts}

async def retry_node(state: GraphState) -> Dict[str, Any]:
    """
    Increments retry values for low-confidence results.
    """
    job_id = state["job_id"]
    await write_audit_log(
        job_id, 
        "retry_handler", 
        "RETRY", 
        f"Retrying Agent 1. Attempt {state.get('retry_count', 0)}"
    )
    
    return {"status": "RETRYING"}

async def agent3_node(state: GraphState) -> Dict[str, Any]:
    """
    Node for Agent 3. Generates Agile User Stories using story contexts.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "agent3", "STARTED", "Agent 3 User Story Generation initiated.")
    
    input_data = {
        "epics": state["epics"],
        "features": state["features"],
        "hierarchy": state["hierarchy"],
        "requirements": state["requirements"],
        "story_contexts": state.get("story_contexts", [])
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
    Human Review Interrupt node. Pauses execution before exporting story contexts.
    Uses LangGraph interrupt() mechanism for pausable execution.
    """
    job_id = state["job_id"]
    logger.info(f"Pipeline paused for job {job_id}. Awaiting manual approval.")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        stmt = update(Job).where(Job.id == job_id).values(status="HUMAN_REVIEW")
        await session.execute(stmt)
        await session.commit()

    await write_audit_log(job_id, "human_review", "PENDING", "Pipeline execution paused. Awaiting human approval.")
    return {"status": "HUMAN_REVIEW", "approval_status": "PENDING"}

async def export_node(state: GraphState) -> Dict[str, Any]:
    """
    Executes structured JSON file export with Master Context and Story Contexts.
    """
    job_id = state["job_id"]
    await write_audit_log(job_id, "export", "STARTED", "Export execution started.")
    
    # Save state outcome to job table
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        stmt = update(Job).where(Job.id == job_id).values(status="COMPLETED")
        await session.execute(stmt)
        await session.commit()

    await write_audit_log(job_id, "export", "COMPLETED", "User stories and contexts exported successfully to DB. Execution finished.")
    return {"status": "COMPLETED", "approval_status": "APPROVED"}

async def fail_node(state: GraphState) -> Dict[str, Any]:
    """
    Fail safe terminal state. Triggered when confidence threshold fails after max retries.
    """
    job_id = state["job_id"]
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        stmt = update(Job).where(Job.id == job_id).values(
            status="FAILED",
            error_message="Confidence threshold failure after max retries."
        )
        await session.execute(stmt)
        await session.commit()

    await write_audit_log(job_id, "pipeline", "FAILED", "Workflow aborted due to low confidence rating.")
    return {"status": "FAILED"}

# --- Graph Routing Functions ---

def _route_after_confidence_check(state: GraphState) -> str:
    """
    Route after confidence check node.
    """
    status = state.get("status")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if status == "RETRYING" and retry_count < max_retries:
        return "retry"
    elif retry_count >= max_retries:
        return "fail"
    else:
        return "agent2"

# --- Graph Compilation ---

workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("ingest", ingest_node)
workflow.add_node("agent1", agent1_node)
workflow.add_node("confidence_check", confidence_check_node)
workflow.add_node("retry", retry_node)
workflow.add_node("agent2", agent2_node)
workflow.add_node("merge_outputs", merge_outputs_node)
workflow.add_node("build_story_contexts", build_story_contexts_node)
workflow.add_node("agent3", agent3_node)
workflow.add_node("agent4", agent4_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("export", export_node)
workflow.add_node("fail", fail_node)

# Configure Edges
workflow.set_entry_point("ingest")
workflow.add_edge("ingest", "agent1")
workflow.add_edge("agent1", "confidence_check")

# Route after confidence check
workflow.add_conditional_edges(
    "confidence_check",
    _route_after_confidence_check,
    {
        "retry": "retry",
        "agent2": "agent2",
        "fail": "fail"
    }
)
workflow.add_edge("retry", "agent1")

# Main flow: Agent2 → Merge → Build Story Contexts → Agent3
workflow.add_edge("agent2", "merge_outputs")
workflow.add_edge("merge_outputs", "build_story_contexts")
workflow.add_edge("build_story_contexts", "agent3")

# Agent3 → Agent4
workflow.add_edge("agent3", "agent4")

# Route after Validation
workflow.add_conditional_edges(
    "agent4",
    route_after_validation,
    {
        "export_node": "human_review",
        "human_review_node": "human_review"
    }
)

# Human review → Export
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
# Confidence check after Agent 1 validates quality before proceeding to Agent 2.
# Merge and Story Context building are non-LLM orchestration nodes.
# Master Context and Story Contexts are created for optimal token efficiency to Agent 3.

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
