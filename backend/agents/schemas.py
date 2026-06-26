from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Agent 1 (Requirement Intelligence) Schemas ---

class ExtractedRequirement(BaseModel):
    id: str = Field(..., description="Unique shorthand ID, e.g. REQ-001")
    content: str = Field(..., description="The clear requirement statement")
    actors: List[str] = Field(default_factory=list, description="Actors involved in this requirement")
    business_rules: List[str] = Field(default_factory=list, description="Associated business logic constraints")

class RequirementIntelligenceOutput(BaseModel):
    requirements: List[ExtractedRequirement] = Field(..., description="List of extracted system requirements")
    actors: List[str] = Field(default_factory=list, description="Global actors identified in the document")
    business_rules: List[str] = Field(default_factory=list, description="General business rules identified")
    ambiguities: List[str] = Field(default_factory=list, description="Unclear statements needing clarification")
    conflicts: List[str] = Field(default_factory=list, description="Contradicting elements identified within requirements")
    confidence_score: float = Field(..., description="Quality/completeness confidence score (0.0 to 1.0)")


# --- Agent 1 (NEW: Requirement Intelligence v2) Schemas ---

class FunctionalRequirement(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., FR-001")
    name: str = Field(..., description="Requirement name")
    description: str = Field(..., description="Clear requirement statement")
    source_text: str = Field(..., description="Exact quote from original requirement text")
    traceability_id: str = Field(..., description="fingerprint#offset for traceability")

class NonFunctionalRequirement(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., NFR-001")
    category: str = Field(..., description="Category: Performance, Security, Reliability, Availability, Maintainability, Scalability, Compliance, Accessibility, Portability, Usability")
    name: str = Field(..., description="NFR name")
    description: str = Field(..., description="Clear requirement statement")
    source_text: str = Field(..., description="Exact quote from original requirement text")
    traceability_id: str = Field(..., description="fingerprint#offset for traceability")

class BusinessRule(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., BR-001")
    type: str = Field(..., description="Rule type: Validation, Policy, Constraint, Permission, Threshold, Calculation, State Transition")
    rule: str = Field(..., description="Concise rule statement")
    description: str = Field(..., description="Detailed description")
    source_text: str = Field(..., description="Exact quote from original requirement text")
    traceability_id: str = Field(..., description="fingerprint#offset for traceability")

class Actor(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., ACT-001")
    name: str = Field(..., description="Actor name")
    type: str = Field(..., description="Type: Human, System, External API")
    description: str = Field(..., description="Actor description and responsibilities")

class Dependency(BaseModel):
    id: str = Field(..., description="Unique ID, e.g., DEP-001")
    source: str = Field(..., description="Source requirement ID")
    target: str = Field(..., description="Target requirement ID")
    type: str = Field(..., description="Type: Blocking, Sequential, Parallel")
    description: str = Field(..., description="Dependency relationship description")

class Conflict(BaseModel):
    requirement: str = Field(..., description="Conflicting requirement ID or name")
    issue: str = Field(..., description="Description of the conflict")

class Ambiguity(BaseModel):
    requirement: str = Field(..., description="Requirement ID with ambiguity")
    term: str = Field(..., description="Ambiguous term")
    issue: str = Field(..., description="Why it's ambiguous and recommended clarification")

class MissingRequirement(BaseModel):
    area: str = Field(..., description="Missing requirement area")
    description: str = Field(..., description="Description of what's missing")

class RetryMetadata(BaseModel):
    attempts: int = Field(..., description="Number of attempts made")
    max_attempts: int = Field(..., description="Maximum attempts allowed")
    target_confidence: int = Field(..., description="Target confidence score")
    status: str = Field(..., description="Status: SUCCESS, RETRIED, MAX_RETRIES_REACHED")
    recommendation: str = Field(..., description="Recommendation for next steps")

class ValidationContext(BaseModel):
    conflicts: List[Conflict] = Field(default_factory=list, description="Detected conflicts")
    ambiguities: List[Ambiguity] = Field(default_factory=list, description="Detected ambiguities")
    missing_requirements: List[MissingRequirement] = Field(default_factory=list, description="Missing important requirements")
    domain: str = Field(..., description="Business domain classification")
    confidence_score: int = Field(..., description="Overall confidence score (0-100)")
    retry_metadata: RetryMetadata = Field(..., description="Retry attempt metadata")

class PrimaryInput(BaseModel):
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list, description="Extracted functional requirements")
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list, description="Extracted non-functional requirements")
    business_rules: List[BusinessRule] = Field(default_factory=list, description="Extracted business rules")
    actors: List[Actor] = Field(default_factory=list, description="Identified actors and stakeholders")
    dependencies: List[Dependency] = Field(default_factory=list, description="Requirement dependencies")

class Agent1RequirementIntelligenceOutput(BaseModel):
    """Agent 1 output conforming to exact specification"""
    primary_input: PrimaryInput = Field(..., description="Extracted requirements, rules, actors, dependencies")
    validation_context: ValidationContext = Field(..., description="Quality validation, conflicts, ambiguities, domain, confidence")


# --- Agent 2 (Epic & Feature Planner) Schemas ---

class EpicPlan(BaseModel):
    id: str = Field(..., description="Epic ID, e.g., EPIC-1")
    name: str = Field(..., description="Descriptive high-level epic title")
    description: str = Field(..., description="Detailed description of the epic scope")

class FeaturePlan(BaseModel):
    id: str = Field(..., description="Feature ID, e.g., FEAT-1")
    epic_id: str = Field(..., description="Associated Epic ID")
    name: str = Field(..., description="Feature title")
    description: str = Field(..., description="Feature summary details")
    priority: str = Field(default="Medium", description="Priority level: High, Medium, Low")

class TraceMapping(BaseModel):
    requirement_id: str = Field(..., description="Shorthand requirement ID, e.g. REQ-001")
    feature_id: str = Field(..., description="Target feature identifier mapping, e.g. FEAT-1")

class RequirementMapping(BaseModel):
    requirement_id: str = Field(..., description="Shorthand requirement ID, e.g. REQ-001")
    requirement_content: str = Field(..., description="The requirement statement")
    epic_id: str = Field(..., description="Associated Epic ID")
    feature_id: str = Field(..., description="Associated Feature ID")

class EpicHierarchy(BaseModel):
    epic_id: str = Field(..., description="Epic ID")
    feature_ids: List[str] = Field(default_factory=list, description="List of feature IDs under this epic")
    requirement_ids: List[str] = Field(default_factory=list, description="List of requirement IDs mapped to features in this epic")

class Dependency(BaseModel):
    dependent_feature_id: str = Field(..., description="Feature that depends on another")
    dependency_feature_id: str = Field(..., description="Feature that is depended upon")
    dependency_type: str = Field(default="blocks", description="Type of dependency: blocks, extends, requires, related")

class FeaturePriority(BaseModel):
    feature_id: str = Field(..., description="Feature ID")
    priority: str = Field(..., description="Priority level: High, Medium, Low")

class CoverageReport(BaseModel):
    total_requirements: int = Field(..., description="Total requirements from Agent-1")
    mapped_requirements: int = Field(..., description="Requirements successfully mapped to features")
    unmapped_requirements: int = Field(..., description="Requirements not mapped to any feature")
    coverage_percentage: float = Field(..., description="Coverage percentage: (mapped / total) * 100")

class Metadata(BaseModel):
    generated_by: str = Field(default="Agent-2", description="Component that generated this output")
    generated_timestamp: str = Field(..., description="ISO 8601 timestamp of generation")
    domain: str = Field(default="", description="Business domain context from Agent-1")
    version: str = Field(default="1.0", description="Output format version")
    model_name: str = Field(default="", description="LLM model name used")
    confidence_score: float = Field(..., description="Overall confidence score (0.0 to 1.0)")

class TraceabilityMatrix(BaseModel):
    requirement_id: str = Field(..., description="Requirement ID from Agent-1")
    epic_id: str = Field(..., description="Epic ID")
    feature_id: str = Field(..., description="Feature ID")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent feature IDs")

class EpicFeaturePlannerOutput(BaseModel):
    epics: List[EpicPlan] = Field(..., description="List of proposed epics")
    features: List[FeaturePlan] = Field(..., description="List of features grouped under epics")
    hierarchy: List[TraceMapping] = Field(..., description="Traceability list mapping requirements to features")
    requirement_mapping: List[RequirementMapping] = Field(default_factory=list, description="Detailed requirement to feature mappings")
    epic_hierarchy: List[EpicHierarchy] = Field(default_factory=list, description="Epic-level hierarchy with feature and requirement groupings")
    dependencies: List[Dependency] = Field(default_factory=list, description="Feature-to-feature dependencies")
    priority: List[FeaturePriority] = Field(default_factory=list, description="Priority assignments for each feature")
    coverage_report: CoverageReport = Field(..., description="Coverage analysis report")
    metadata: Metadata = Field(..., description="Generation metadata including confidence score")
    traceability_matrix: List[TraceabilityMatrix] = Field(default_factory=list, description="Complete traceability matrix for story generation")

# --- Agent 3 (User Story Generator) Schemas ---

class AcceptanceCriteria(BaseModel):
    scenario: str = Field(..., description="Scenario description")
    given: str = Field(..., description="Preconditions")
    when: str = Field(..., description="Trigger actions")
    then: str = Field(..., description="Expected postconditions")

class UserStory(BaseModel):
    id: str = Field(..., description="Story ID, e.g., STORY-1")
    epic_id: str = Field(..., description="Parent epic reference ID")
    feature_id: str = Field(..., description="Parent feature reference ID")
    title: str = Field(..., description="Functional title of user story")
    user_story_text: str = Field(..., description="As a... I want to... So that... standard template")
    acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list, description="Acceptance criteria list")
    trace_mappings: List[str] = Field(..., description="Reference requirement IDs, e.g., ['REQ-001']")

class UserStoryGeneratorOutput(BaseModel):
    user_stories: List[UserStory] = Field(..., description="Generated Agile user stories list")
    plain_text_summary: str = Field(..., description="Narrative summary highlighting structural updates")

# --- Orchestrator (MasterContext & StoryContext) Schemas ---

class StoryContext(BaseModel):
    story_id: str = Field(..., description="Unique story context ID")
    requirement_id: str = Field(..., description="Associated requirement ID from Agent-1")
    requirement: str = Field(..., description="Requirement content")
    epic: Dict[str, Any] = Field(..., description="Epic information")
    feature: Dict[str, Any] = Field(..., description="Feature information")
    actor: str = Field(default="", description="Primary actor for this requirement")
    business_rules: List[str] = Field(default_factory=list, description="Applicable business rules")
    dependencies: List[str] = Field(default_factory=list, description="List of dependent feature IDs")
    priority: str = Field(default="Medium", description="Inherited priority from feature")
    validation: Dict[str, Any] = Field(default_factory=dict, description="Validation context from Agent-1")
    traceability: Dict[str, Any] = Field(default_factory=dict, description="Traceability information")

class MasterContext(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    requirements: List[Dict[str, Any]] = Field(default_factory=list, description="Requirements from Agent-1")
    actors: List[str] = Field(default_factory=list, description="Global actors from Agent-1")
    business_rules: List[str] = Field(default_factory=list, description="Global business rules from Agent-1")
    validation_context: Dict[str, Any] = Field(default_factory=dict, description="Validation context from Agent-1")
    epics: List[EpicPlan] = Field(default_factory=list, description="Epics from Agent-2")
    features: List[FeaturePlan] = Field(default_factory=list, description="Features from Agent-2")
    hierarchy: List[EpicHierarchy] = Field(default_factory=list, description="Epic hierarchy from Agent-2")
    priority: List[FeaturePriority] = Field(default_factory=list, description="Priority assignments from Agent-2")
    coverage_report: CoverageReport = Field(..., description="Coverage report from Agent-2")
    dependencies: List[Dependency] = Field(default_factory=list, description="Dependencies from Agent-2")
    metadata: Metadata = Field(..., description="Metadata from Agent-2")
    traceability_matrix: List[TraceabilityMatrix] = Field(default_factory=list, description="Traceability matrix from Agent-2")
    created_at: str = Field(..., description="ISO 8601 timestamp of master context creation")

# INTEGRATION NOTE
# All pipeline agents serialize their results into these Pydantic models.
# Keep schema names and attributes stable across updates to avoid breaking LangGraph state parsing.
