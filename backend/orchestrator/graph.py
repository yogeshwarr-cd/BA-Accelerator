from typing import Dict, Any, List
from datetime import datetime
from functools import wraps
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestrator.state import GraphState
from backend.shared.logger import get_logger

logger = get_logger(__name__)

pipeline_debug_state: Dict[str, Dict[str, Any]] = {}


def _append_debug_entry(job_id: str, node_name: str, status: str, output: Dict[str, Any] = None, message: str = None) -> None:
    if job_id not in pipeline_debug_state:
        pipeline_debug_state[job_id] = {
            "job_id": job_id,
            "nodes": [],
            "latest_status": "PENDING",
            "error_message": None,
        }

    entry = {
        "node": node_name,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "output": output or {},
    }
    if message:
        entry["message"] = message

    pipeline_debug_state[job_id]["nodes"].append(entry)
    pipeline_debug_state[job_id]["latest_status"] = status
    if status == "FAILED":
        pipeline_debug_state[job_id]["error_message"] = message


def reset_pipeline_debug_state(job_id: str) -> None:
    pipeline_debug_state[job_id] = {
        "job_id": job_id,
        "nodes": [],
        "latest_status": "PENDING",
        "error_message": None,
    }


def get_pipeline_debug_state(job_id: str) -> Dict[str, Any]:
    return pipeline_debug_state.get(job_id, {
        "job_id": job_id,
        "nodes": [],
        "latest_status": "UNKNOWN",
        "error_message": None,
    })


def debug_node(node_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(state: GraphState) -> Dict[str, Any]:
            job_id = state.get("job_id", "")
            logger.info(f"[graph] {node_name} node started for job {job_id}")
            _append_debug_entry(job_id, node_name, "STARTED")
            try:
                output = await func(state)
                _append_debug_entry(job_id, node_name, "COMPLETED", output=output)
                return output
            except Exception as exc:
                _append_debug_entry(job_id, node_name, "FAILED", output={}, message=str(exc))
                raise
        return wrapper
    return decorator


@debug_node("ingest")
async def ingest_node(state: GraphState) -> Dict[str, Any]:
    return {"status": "RUNNING"}


@debug_node("requirement_repository")
async def requirement_repository_node(state: GraphState) -> Dict[str, Any]:
    return {"requirement_package": {"package_id": f"pkg-{state.get('fingerprint','')}", "fingerprint": state.get('fingerprint'), "source_type": state.get('source_type')}}


@debug_node("requirement_package_builder")
async def requirement_package_builder_node(state: GraphState) -> Dict[str, Any]:
    return {
        "requirement_package": {
            "package_id": f"pkg-{state.get('fingerprint','')}",
            "job_id": state.get("job_id"),
            "fingerprint": state.get("fingerprint"),
            "source_type": state.get("source_type"),
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    }


@debug_node("agent1")
async def agent1_node(state: GraphState) -> Dict[str, Any]:
    return {"agent1_output": {}, "requirements": []}


@debug_node("agent2")
async def agent2_node(state: GraphState) -> Dict[str, Any]:
    return {"agent2_output": {}, "epics": [], "features": [], "traceability_matrix": []}


@debug_node("traceability_matrix_builder")
async def traceability_matrix_builder_node(state: GraphState) -> Dict[str, Any]:
    return {"traceability_matrix": state.get("traceability_matrix", [])}


@debug_node("story_packet_builder")
async def story_packet_builder_node(state: GraphState) -> Dict[str, Any]:
    return {"story_packets": [], "status": "COMPLETED"}


workflow = StateGraph(GraphState)
workflow.add_node("ingest", ingest_node)
workflow.add_node("requirement_repository", requirement_repository_node)
workflow.add_node("requirement_package_builder", requirement_package_builder_node)
workflow.add_node("agent1", agent1_node)
workflow.add_node("agent2", agent2_node)
workflow.add_node("traceability_matrix_builder", traceability_matrix_builder_node)
workflow.add_node("story_packet_builder", story_packet_builder_node)

workflow.set_entry_point("ingest")
workflow.add_edge("ingest", "requirement_repository")
workflow.add_edge("requirement_repository", "requirement_package_builder")
workflow.add_edge("requirement_package_builder", "agent1")
workflow.add_edge("agent1", "agent2")
workflow.add_edge("agent2", "traceability_matrix_builder")
workflow.add_edge("traceability_matrix_builder", "story_packet_builder")
workflow.add_edge("story_packet_builder", END)

memory_store = MemorySaver()

pipeline_graph = workflow.compile(checkpointer=memory_store)
