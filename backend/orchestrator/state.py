from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PipelineState(BaseModel):
    """Pydantic model used as a clear contract for pipeline data exchange between nodes.
    Nodes should update only the fields they own and return JSON-serializable dicts.
    """
    job_id: str
    source_type: Optional[str] = ""
    raw_text: Optional[str] = ""
    fingerprint: Optional[str] = ""

    # Requirement Package (pre-Agent-1)
    requirement_package: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Agent 1 outputs
    agent1_output: Optional[Dict[str, Any]] = Field(default_factory=dict)
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    actors: List[str] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)
    ambiguities: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = 0.0

    # Agent 2 outputs
    agent2_output: Optional[Dict[str, Any]] = Field(default_factory=dict)
    epics: List[Dict[str, Any]] = Field(default_factory=list)
    features: List[Dict[str, Any]] = Field(default_factory=list)
    hierarchy: List[Dict[str, Any]] = Field(default_factory=list)
    requirement_mapping: List[Dict[str, Any]] = Field(default_factory=list)
    epic_hierarchy: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    priority: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_report: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    traceability_matrix: List[Dict[str, Any]] = Field(default_factory=list)

    # Story Packet outputs (stop after building these)
    story_packets: List[Dict[str, Any]] = Field(default_factory=list)

    # Execution tracing
    retry_count: int = 0
    max_retries: int = 3
    status: str = Field(default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    error_message: Optional[str] = None


class GraphState(TypedDict):
    """
    TypedDict used by LangGraph StateGraph construction. Keep keys JSON-serializable.
    """
    job_id: str
    source_type: str
    raw_text: str
    fingerprint: str

    requirement_package: Dict[str, Any]

    agent1_output: Dict[str, Any]
    requirements: List[Dict[str, Any]]
    actors: List[str]
    business_rules: List[str]
    ambiguities: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    confidence_score: float

    agent2_output: Dict[str, Any]
    epics: List[Dict[str, Any]]
    features: List[Dict[str, Any]]
    hierarchy: List[Dict[str, Any]]
    requirement_mapping: List[Dict[str, Any]]
    epic_hierarchy: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    priority: List[Dict[str, Any]]
    coverage_report: Dict[str, Any]
    metadata: Dict[str, Any]
    traceability_matrix: List[Dict[str, Any]]

    story_packets: List[Dict[str, Any]]

    retry_count: int
    max_retries: int
    status: str
    error_message: Optional[str]

# INTEGRATION NOTE
# `PipelineState` is a convenience Pydantic model for local code clarity.
# `GraphState` is the TypedDict used by the LangGraph StateGraph runtime.
