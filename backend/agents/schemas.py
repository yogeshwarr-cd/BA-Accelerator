from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class Requirement(BaseModel):
    id: str = Field(..., description="Requirement identifier")
    text: str = Field(..., description="Requirement statement")


class Epic(BaseModel):
    id: str = Field(..., description="Epic identifier")
    name: str = Field(..., description="Epic title")


class Feature(BaseModel):
    id: str = Field(..., description="Feature identifier")
    name: str = Field(..., description="Feature title")


class AcceptanceCriteria(BaseModel):
    statement: str = Field(..., description="Single acceptance criterion statement")
    scenario: str = Field(default="", description="Scenario description")
    given: str = Field(default="", description="Preconditions")
    when: str = Field(default="", description="Trigger actions")
    then: str = Field(default="", description="Expected postconditions")


class Metadata(BaseModel):
    generated_by: str = Field(default="Agent-2", description="Component that generated this output")
    generated_timestamp: str = Field(..., description="ISO 8601 timestamp of generation")
    domain: str = Field(default="", description="Business domain context from Agent-1")
    version: str = Field(default="1.0", description="Output format version")
    model_name: str = Field(default="", description="LLM model name used")
    confidence_score: float = Field(..., description="Overall confidence score (0.0 to 1.0)")
    source_story_count: int = Field(default=0, description="Number of story contexts processed")

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return value

    def __getitem__(self, item: str) -> Any:
        return self.model_dump().get(item)

    def get(self, item: str, default: Any = None) -> Any:
        return self.model_dump().get(item, default)

    def keys(self):
        return self.model_dump().keys()

    def values(self):
        return self.model_dump().values()

    def items(self):
        return self.model_dump().items()


class Traceability(BaseModel):
    requirement_id: str = Field(default="", description="Requirement identifier")
    epic_id: str = Field(default="", description="Epic identifier")
    feature_id: str = Field(default="", description="Feature identifier")


class UserStoryContent(BaseModel):
    actor: str = Field(default="User", description="Primary actor")
    goal: str = Field(default="", description="Story goal")
    benefit: str = Field(default="", description="Business benefit")


class GeneratedUserStory(BaseModel):
    story_id: str = Field(..., description="Generated story identifier")
    traceability: Traceability = Field(default_factory=Traceability, description="Requirement, epic, and feature identifiers")
    epic: str = Field(..., description="Epic title")
    feature: str = Field(..., description="Feature title")
    user_story: UserStoryContent = Field(default_factory=UserStoryContent, description="Actor, goal, and benefit")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria statements")
    definition_of_done: List[str] = Field(default_factory=list, description="Definition of done checklist")
    summary: str = Field(..., description="Concise story summary")
    priority: str = Field(default="Medium", description="Story priority")
    version: int = Field(default=1, description="Story version")
    metadata: Metadata = Field(default_factory=Metadata, description="Generation metadata")


class Response(BaseModel):
    stories: List[GeneratedUserStory] = Field(default_factory=list, description="Generated stories")
    summary: str = Field(default="", description="Narrative summary")


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

    def __getitem__(self, item: str) -> Any:
        return self.model_dump().get(item)

    def get(self, item: str, default: Any = None) -> Any:
        return self.model_dump().get(item, default)

    def keys(self):
        return self.model_dump().keys()

    def values(self):
        return self.model_dump().values()

    def items(self):
        return self.model_dump().items()

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
    story_context_id: str = Field(default="", description="Unique story context ID")
    story_id: str = Field(default="", description="Unique story context ID")
    requirement_id: str = Field(default="", description="Associated requirement ID from Agent-1")
    requirement: Any = Field(default_factory=dict, description="Requirement content")
    epic: Any = Field(default_factory=dict, description="Epic information")
    feature: Any = Field(default_factory=dict, description="Feature information")
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
