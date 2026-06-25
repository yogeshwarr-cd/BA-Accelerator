from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

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

class TraceMapping(BaseModel):
    requirement_id: str = Field(..., description="Shorthand requirement ID, e.g. REQ-001")
    feature_id: str = Field(..., description="Target feature identifier mapping, e.g. FEAT-1")

class EpicFeaturePlannerOutput(BaseModel):
    epics: List[EpicPlan] = Field(..., description="List of proposed epics")
    features: List[FeaturePlan] = Field(..., description="List of features grouped under epics")
    hierarchy: List[TraceMapping] = Field(..., description="Traceability list mapping requirements to features")

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

# INTEGRATION NOTE
# All pipeline agents serialize their results into these Pydantic models.
# Keep schema names and attributes stable across updates to avoid breaking LangGraph state parsing.
