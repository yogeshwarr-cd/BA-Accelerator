from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    """
    State contract for LangGraph orchestration.
    Single source of truth passed across pipeline agents.
    """
    job_id: str
    source_type: str
    raw_text: str
    fingerprint: str
    
    # Agent 1 outputs
    requirements: List[Dict[str, Any]]
    actors: List[str]
    business_rules: List[str]
    ambiguities: List[str]
    conflicts: List[str]
    confidence_score: float
    
    # Agent 2 outputs
    epics: List[Dict[str, Any]]
    features: List[Dict[str, Any]]
    hierarchy: List[Dict[str, Any]]
    
    # Agent 3 outputs
    user_stories: List[Dict[str, Any]]
    plain_text_summary: str
    
    # Agent 4 (validation) outputs
    validation_results: Dict[str, Any]
    quality_score: float
    is_approved: bool
    
    # Execution tracing
    retry_count: int
    max_retries: int
    status: str  # PENDING, RUNNING, HUMAN_REVIEW, COMPLETED, FAILED
    error_message: Optional[str]
    human_approved: bool

# INTEGRATION NOTE
# StateGraph is instantiated using this TypedDict interface.
# Do not store class instances here; all state parameters must be JSON serializable.
